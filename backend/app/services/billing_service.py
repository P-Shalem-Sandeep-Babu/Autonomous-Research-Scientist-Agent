import logging
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import User, BillingTransaction

logger = logging.getLogger("arsa.billing")

PIPELINE_RUN_COST_USD = 2.50
TIER_PRICING = {
    "free": 0.0,
    "pro": 49.0,
    "enterprise": 299.0
}
TIER_COMPUTE_QUOTA = {
    "free": 100.0,
    "pro": 500.0,
    "enterprise": 2500.0
}
TIER_TOKEN_QUOTA = {
    "free": 500_000,
    "pro": 5_000_000,
    "enterprise": 50_000_000
}

class BillingService:
    @staticmethod
    def check_and_deduct_pipeline_funds(
        db: Session, 
        user: User, 
        project_id: int
    ) -> Tuple[bool, str, Optional[BillingTransaction]]:
        """
        Pre-flight gatekeeper enforcing commercial operations, quotas, and ledger balance.
        Prevents unauthorized runs and financial loss from API abuse.
        """
        if not user.is_active:
            return False, "Account is inactive or suspended. Please contact enterprise support.", None

        # Check GPU compute quota limit
        used_gpu = getattr(user, "compute_used_gpu_hours", 0.0) or 0.0
        quota_gpu = getattr(user, "compute_quota_gpu_hours", 100.0) or 100.0
        if used_gpu >= quota_gpu:
            return (
                False, 
                f"GPU compute allocation exhausted ({used_gpu:.1f}/{quota_gpu:.1f} hours). Please upgrade your quota in billing settings.", 
                None
            )

        tier = getattr(user, "subscription_tier", "free") or "free"

        # Pro and Enterprise tiers include unlimited runs
        if tier in ("pro", "enterprise"):
            # Record audit transaction with $0 charge
            tx = BillingTransaction(
                user_id=user.id,
                amount_usd=0.0,
                transaction_type="pipeline_run",
                status="completed",
                description=f"Autonomous pipeline run for project #{project_id} ({tier.title()} subscription benefit)",
                reference_id=str(project_id)
            )
            user.compute_used_gpu_hours = used_gpu + 0.25
            db.add(tx)
            db.commit()
            db.refresh(user)
            logger.info(f"Authorized pipeline run for user #{user.id} under {tier.title()} tier.")
            return True, f"Authorized under {tier.title()} plan (unlimited execution).", tx

        # Free tier: requires balance >= PIPELINE_RUN_COST_USD
        balance = getattr(user, "balance_usd", 0.0) or 0.0
        if balance < PIPELINE_RUN_COST_USD:
            return (
                False,
                f"Insufficient funds (${balance:.2f} available, ${PIPELINE_RUN_COST_USD:.2f} required). Please top up your balance or upgrade to Pro for unlimited runs.",
                None
            )

        # Atomically deduct the run cost and add transaction record
        user.balance_usd = balance - PIPELINE_RUN_COST_USD
        user.compute_used_gpu_hours = used_gpu + 0.25
        user.token_used = (getattr(user, "token_used", 0) or 0) + 12_500

        tx = BillingTransaction(
            user_id=user.id,
            amount_usd=-PIPELINE_RUN_COST_USD,
            transaction_type="pipeline_run",
            status="completed",
            description=f"Commercial execution fee for autonomous pipeline #{project_id}",
            reference_id=str(project_id)
        )
        db.add(tx)
        db.commit()
        db.refresh(user)
        logger.info(f"Deducted ${PIPELINE_RUN_COST_USD:.2f} from user #{user.id}. Remaining balance: ${user.balance_usd:.2f}")
        return True, f"Authorized. ${PIPELINE_RUN_COST_USD:.2f} deducted. Balance: ${user.balance_usd:.2f}.", tx

    @staticmethod
    def deposit_funds(
        db: Session, 
        user: User, 
        amount_usd: float, 
        payment_method: str = "card_mock"
    ) -> BillingTransaction:
        """Add credits to the user's commercial operations balance."""
        if amount_usd <= 0:
            raise ValueError("Deposit amount must be strictly greater than $0.00")

        current_balance = getattr(user, "balance_usd", 0.0) or 0.0
        user.balance_usd = current_balance + amount_usd

        tx = BillingTransaction(
            user_id=user.id,
            amount_usd=amount_usd,
            transaction_type="deposit",
            status="completed",
            description=f"Balance deposit via {payment_method.replace('_', ' ').title()}",
            reference_id=f"DEP-{user.id}-{int(amount_usd*100)}"
        )
        db.add(tx)
        db.commit()
        db.refresh(user)
        db.refresh(tx)
        logger.info(f"User #{user.id} deposited ${amount_usd:.2f}. New balance: ${user.balance_usd:.2f}")
        return tx

    @staticmethod
    def upgrade_subscription(
        db: Session, 
        user: User, 
        target_tier: str
    ) -> BillingTransaction:
        """Upgrade or update user subscription tier and recalculate quotas."""
        target_tier = target_tier.lower()
        if target_tier not in TIER_PRICING:
            raise ValueError(f"Invalid subscription tier '{target_tier}'. Must be one of: {list(TIER_PRICING.keys())}")

        price = TIER_PRICING[target_tier]
        user.subscription_tier = target_tier
        user.compute_quota_gpu_hours = TIER_COMPUTE_QUOTA[target_tier]
        user.token_quota = TIER_TOKEN_QUOTA[target_tier]

        tx = BillingTransaction(
            user_id=user.id,
            amount_usd=-price if price > 0 else 0.0,
            transaction_type="subscription_charge",
            status="completed",
            description=f"Subscription upgrade to {target_tier.title()} Plan (${price:.2f}/mo)",
            reference_id=f"SUB-{target_tier.upper()}-{user.id}"
        )
        db.add(tx)
        db.commit()
        db.refresh(user)
        db.refresh(tx)
        logger.info(f"User #{user.id} upgraded to {target_tier.title()} subscription.")
        return tx

    @staticmethod
    def get_summary(db: Session, user: User) -> Dict[str, Any]:
        """Retrieve complete billing overview, usage metrics, and recent transaction history."""
        transactions = (
            db.query(BillingTransaction)
            .filter(BillingTransaction.user_id == user.id)
            .order_by(BillingTransaction.created_at.desc())
            .limit(20)
            .all()
        )
        return {
            "subscription_tier": getattr(user, "subscription_tier", "free") or "free",
            "balance_usd": getattr(user, "balance_usd", 25.0) or 25.0,
            "compute_quota_gpu_hours": getattr(user, "compute_quota_gpu_hours", 100.0) or 100.0,
            "compute_used_gpu_hours": getattr(user, "compute_used_gpu_hours", 0.0) or 0.0,
            "token_quota": getattr(user, "token_quota", 500_000) or 500_000,
            "token_used": getattr(user, "token_used", 0) or 0,
            "transactions": transactions
        }

billing_service = BillingService()
