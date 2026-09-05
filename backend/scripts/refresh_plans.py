import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect("arsa.db")
c = conn.cursor()

PLANS_BY_PROJECT = {
    1: {
        "topic": "Brain Tumor MRI Multi-Modal Segmentation and Sub-Region Volumetry",
        "title": "Tri-Planar Axial-Mamba UNet for Parameter-Efficient 3D Brain Tumor Segmentation",
        "target_hypothesis": "Tri-Planar Axial-Mamba UNet Architecture for Parameter-Efficient 3D MRI Segmentation",
        "target_gap": "GAP-01: 3D Volumetric Memory Bottleneck & Inter-Slice Context Loss in 2D Slices",
        "roadmap": [
            {
                "phase": "Phase 1",
                "step": "Phase 1: Multi-Modal MRI Preprocessing & Spatial Harmonization",
                "category": "Data Pipeline",
                "milestone": "Harmonized 1mm3 Isotropic Cohort",
                "details": "Ingest 369 multimodal MRI subjects from BraTS 2020 and 262 subjects from TCGA-GBM. Apply N4ITK bias field correction to eliminate scanner coil inhomogeneity. Co-register T1, T1ce, and T2 sequences to the FLAIR template, followed by rigid skull-stripping. Resample all volumes to 1mm3 isotropic voxel resolution (240x240x155 grid). Apply intensity z-score normalization within brain-masked voxels and clamp extreme contrast outliers between the 1st and 99th percentiles.",
                "inputs": "BraTS 2020 (369 scans) + TCGA-GBM (262 scans)",
                "algorithm": "N4ITK Bias Correction + SRI24 Rigid Registration + Robust Z-Scoring",
                "deliverables": "Preprocessed 4-channel HDF5 tensor shards + metadata index CSV",
                "mitigation": "Dynamic intensity percentile clamping prevents numerical divergence from coil boundary artifacts."
            },
            {
                "phase": "Phase 2",
                "step": "Phase 2: Baseline Implementation & State-Space Backbone Setup",
                "category": "Model Architecture",
                "milestone": "Tri-Planar Axial-Mamba UNet Compiled",
                "details": "Implement literature baselines: DR-Unet104 (Colman et al.) with 104 residual convolutional layers and MBDRes-U-Net (Shen et al.) multi-branch residual blocks. Construct the proposed Tri-Planar Axial-Mamba UNet featuring bidirectional state-space selective scan modules (S6) that independently scan axial, sagittal, and coronal planes with linear O(N) memory scaling, coupled with cross-plane gated fusion at each decoder level. Total trainable parameters constrained to 28.4M.",
                "inputs": "4-channel normalized tensor patches (128x128x128)",
                "algorithm": "Bidirectional Selective State-Space (S6) + Tri-Planar Gated Feature Fusion",
                "deliverables": "PyTorch model architecture module + TorchScript graph export",
                "mitigation": "Gradient checkpointing on S6 recurrent projections ensures execution fits comfortably within 24GB VRAM."
            },
            {
                "phase": "Phase 3",
                "step": "Phase 3: Dual-Objective Training & Regularization Protocol",
                "category": "Optimization Protocol",
                "milestone": "50-Epoch Model Convergence",
                "details": "Train models using a composite loss function: L_total = 0.6 * L_Soft-Dice + 0.4 * L_Focal, where Focal loss (gamma=2.0, alpha=0.25) penalizes hard false positives along peritumoral edema boundaries. Optimize using AdamW (lr=10^-4, beta1=0.9, beta2=0.999, weight decay 10^-4) with a 5-epoch linear warmup followed by Cosine Annealing decay down to 10^-6. Execute with mixed precision (AMP FP16), batch size 4, gradient clipping at max norm 1.0, and early stopping patience of 8 epochs.",
                "inputs": "Stratified 70/10/20 train/val/test split (scanner-balanced)",
                "algorithm": "Composite Soft-Dice + Focal Loss with AdamW & Cosine LR Decay",
                "deliverables": "Best checkpoint weights (model_best.pt) + training trajectory tensorboard logs",
                "mitigation": "Per-class Dice weighting (0.4 Enhancing Tumor, 0.3 Edema, 0.3 Necrotic Core) balances severe class imbalance."
            },
            {
                "phase": "Phase 4",
                "step": "Phase 4: Systematic Ablation Suite & Baseline Benchmarking",
                "category": "Ablation Studies",
                "milestone": "Causal Module Contribution Quantified",
                "details": "Conduct 4 rigorous ablation experiments under identical training schedules: (1) Standard 2D DR-Unet104 baseline; (2) Pure 3D CNN (Shen et al. MBDRes-U-Net); (3) Tri-Planar Mamba without cross-plane gating (independent axes only); (4) Full Tri-Planar Axial-Mamba UNet with cross-plane fusion. Record parameter counts, peak VRAM during training, inference latency per volume, and sub-region Dice scores.",
                "inputs": "Held-out BraTS 2020 Validation Partition (n=74)",
                "algorithm": "Module knock-out ablation protocol under fixed random seeds",
                "deliverables": "Ablation comparison metrics table + memory-efficiency scaling curves",
                "mitigation": "Fixed random seeds (seed=42) across all runs guarantee reproducibility and fair comparison."
            },
            {
                "phase": "Phase 5",
                "step": "Phase 5: Cross-Center Out-of-Distribution & Statistical Significance",
                "category": "Statistical Validation",
                "milestone": "Validated Generalization & Hypothesis Verification",
                "details": "Evaluate trained models on the external, out-of-distribution TCGA-GBM clinical cohort to assess scanner generalization without fine-tuning. Compute 5-fold cross-validation statistics, paired two-tailed Wilcoxon signed-rank tests against DR-Unet104 baseline predictions, and 1,000-sample bootstrap 95% confidence intervals for Whole Tumor (WT), Tumor Core (TC), and Enhancing Tumor (ET) Dice scores and 95% Hausdorff Distance (HD95).",
                "inputs": "External TCGA-GBM validation set (n=52) + 5-fold test folds",
                "algorithm": "Paired Wilcoxon Signed-Rank Test + 1000-Iteration Bootstrap CI",
                "deliverables": "Statistical significance report (p-values) + multi-class confusion matrices + HD95 plots",
                "mitigation": "Falsification threshold: If p >= 0.05 or WT Dice < 0.895, the hypothesis is rejected."
            }
        ],
        "metrics": [
            "Dice Similarity Coefficient (Whole Tumor) > 0.914 (vs DR-Unet104: 0.886 | MBDRes-U-Net: 0.892)",
            "Dice Similarity Coefficient (Enhancing Tumor) > 0.845 (vs DR-Unet104: 0.812 | MBDRes-U-Net: 0.825)",
            "Hausdorff Distance 95% (HD95) < 5.2 mm (vs DR-Unet104: 7.8 mm | MBDRes-U-Net: 6.4 mm)",
            "Mean Intersection over Union (mIoU) > 0.842 (vs Baseline: 0.795)",
            "Inference Latency < 45 ms / 3D volume (vs 3D CNN: 142 ms / volume)",
            "Peak Training VRAM < 14.5 GB (vs 3D CNN: 23.8 GB)"
        ],
        "hardware_requirements": {
            "GPU": "1x NVIDIA RTX 4090 (24GB VRAM) or NVIDIA A100 (40GB/80GB)",
            "CPU": "16 vCPUs (AMD EPYC or Intel Xeon)",
            "RAM": "64 GB System RAM",
            "expected_runtime": "2.8 hours (50 epochs, batch size 4, mixed precision)",
            "precision": "Automatic Mixed Precision (AMP FP16 / BF16)",
            "framework": "PyTorch 2.3+ with CUDA 12.2 and MONAI 1.3",
            "storage": "120 GB NVMe SSD for fast cached tensor loading"
        },
        "ablation_matrix": [
            {"variant": "Standard 2D DR-Unet104", "purpose": "Isolates 2D slice baseline without inter-slice or Mamba attention", "dice_expected": "0.886", "vram": "6.2 GB"},
            {"variant": "Full 3D MBDRes-U-Net", "purpose": "Evaluates 3D convolutional baseline with cubic memory complexity", "dice_expected": "0.892", "vram": "23.8 GB"},
            {"variant": "Axial-Mamba (No Cross-Plane Fusion)", "purpose": "Evaluates state-space scanning without cross-plane gating", "dice_expected": "0.903", "vram": "12.1 GB"},
            {"variant": "Proposed Tri-Planar Axial-Mamba UNet", "purpose": "Full proposed model with cross-plane selective gating", "dice_expected": ">0.914", "vram": "14.2 GB"}
        ]
    },
    2: {
        "topic": "Domain-Invariant Multi-Center Brain Tumor Detection",
        "title": "Domain-Adversarial Vision Transformer (DA-ViT) with Gradient Reversal for Multi-Center MRI Invariance",
        "target_hypothesis": "Domain-Adversarial Vision Transformer (DA-ViT) with Gradient Reversal Layer for Scanner Invariance",
        "target_gap": "GAP-01: Multi-Center Scanner Domain Shift (Siemens 3.0T vs Philips 1.5T vs GE)",
        "roadmap": [
            {
                "phase": "Phase 1",
                "step": "Phase 1: Multi-Site Dataset Curation & Scanner Domain Labeling",
                "category": "Data Pipeline",
                "milestone": "Multi-Scanner Labeled Partitions (Siemens, Philips, GE)",
                "details": "Curate 1,251 multi-institutional cases from BraTS 2021 and TCGA-GBM. Annotate each subject with scanner metadata: manufacturer (Siemens, Philips, GE), magnetic field strength (1.5T vs 3.0T), and acquisition site ID. Perform N4ITK bias correction and min-max intensity scaling. Establish a Leave-One-Center-Out (LOCO) evaluation split: Source domain = Siemens (n=680) + GE (n=320); Unseen Target domain = Philips 1.5T (n=251).",
                "inputs": "BraTS 2021 Multi-Center + TCGA-GBM (DICOM metadata)",
                "algorithm": "Scanner Metadata Parser + N4ITK Bias Correction + LOCO Cross-Validation Split",
                "deliverables": "Multi-domain HDF5 partitions + domain-labeled CSV index",
                "mitigation": "Zero Target Domain Leakage: Philips scanner scans are strictly withheld from model training and validation."
            },
            {
                "phase": "Phase 2",
                "step": "Phase 2: Domain-Adversarial Vision Transformer (DA-ViT) Architecture",
                "category": "Model Architecture",
                "milestone": "Dual-Head DA-ViT Network Compiled",
                "details": "Implement standard Vision Transformer (ViT-B/16) pre-trained on FOMO-MRI 50K as feature extractor G_f. Attach two competing heads: (1) Primary Tumor Classifier G_y predicting glioma presence/subtypes; (2) Domain Discriminator G_d predicting scanner manufacturer. Place a Gradient Reversal Layer (GRL) between G_f and G_d with dynamic scheduling parameter lambda_p = 2 / (1 + exp(-10p)) - 1, forcing G_f to learn representations that maximize classification accuracy while minimizing scanner discriminator capability.",
                "inputs": "2D axial multi-parametric slices (224x224x4 channels)",
                "algorithm": "ViT-B/16 Backbone + Gradient Reversal Layer (GRL) + Multi-Layer Domain Discriminator",
                "deliverables": "PyTorch DA-ViT implementation + GRL autograd function",
                "mitigation": "Dynamic lambda scheduling prevents domain adversarial gradients from destabilizing early feature learning."
            },
            {
                "phase": "Phase 3",
                "step": "Phase 3: Minimax Adversarial Optimization & Warmup Schedule",
                "category": "Optimization Protocol",
                "milestone": "Adversarial Equilibrium Attained",
                "details": "Train under minimax objective: min_{theta_f, theta_y} max_{theta_d} L_y(G_y(G_f(x)), y) - lambda * L_d(G_d(G_f(x)), d). Optimizer: AdamW (lr=5e-5 for backbone, 1e-4 for classifier and discriminator heads). Use 10-epoch warm-up on source classification alone before initiating adversarial backpropagation. Total 60 epochs with early stopping based on validation target domain proxy loss.",
                "inputs": "Source Domain Scans (Siemens/GE) with Tumor Labels + Scanner Labels",
                "algorithm": "Minimax GRL Backpropagation + Layer-wise Learning Rate Decay",
                "deliverables": "Trained invariant model checkpoints + domain discrimination confusion matrices",
                "mitigation": "Gradient clipping at 0.5 prevents gradient explosion during adversarial minimax competition."
            },
            {
                "phase": "Phase 4",
                "step": "Phase 4: Multi-Center Baseline Benchmarking & Ablation Experiments",
                "category": "Ablation Studies",
                "milestone": "Scanner Invariance Empirically Proven",
                "details": "Compare DA-ViT against: (1) Empirical Risk Minimization (ERM) ViT without GRL; (2) ResNet-50 with standard data augmentations; (3) AdaBN (Adaptive Batch Normalization); (4) Full DA-ViT. Measure in-domain accuracy (Siemens test), out-of-domain accuracy (Philips 1.5T test), and Domain Classifier Accuracy (where ~33% indicates perfect scanner invariance).",
                "inputs": "Held-out Source Test Set + Unseen Target Domain (Philips 1.5T)",
                "algorithm": "Ablation comparison across 4 domain generalization protocols",
                "deliverables": "Domain generalization performance table + t-SNE latent feature visualization plots",
                "mitigation": "t-SNE cluster separation metric verifies that scanner clusters collapse into unified disease representations."
            },
            {
                "phase": "Phase 5",
                "step": "Phase 5: Clinical Generalization Testing & Robustness Bounds",
                "category": "Statistical Validation",
                "milestone": "Statistically Significant Generalization Certified",
                "details": "Test performance under simulated noise corruptions: Rician noise (sigma in [0.01, 0.08]), motion ghosting artifacts, and field strength downsampling. Perform 10-fold cross-center validation. Conduct paired t-tests and Wilcoxon tests confirming OOD degradation is < 3.5% (compared to > 18.4% drop in ERM baseline).",
                "inputs": "Synthetically corrupted MRI benchmarks + external clinical validation cohort",
                "algorithm": "Robustness Stress Testing + Paired Wilcoxon Signed-Rank Test",
                "deliverables": "Corruption robustness curves + 95% confidence intervals report",
                "mitigation": "Falsification condition: If OOD performance drop exceeds 5% or domain classification accuracy remains > 60%, hypothesis is rejected."
            }
        ],
        "metrics": [
            "In-Domain Classification Accuracy (Siemens 3.0T) > 96.2% (vs Baseline: 95.8%)",
            "Out-of-Distribution Accuracy (Philips 1.5T) > 93.8% (vs Standard ViT: 77.4% | ResNet-50: 74.2%)",
            "Domain Classifier Confusion Entropy > 0.92 (Ideal: 1.0 = completely scanner-invariant)",
            "OOD Performance Drop < 2.5% (vs Baseline Drop: 18.4%)",
            "AUC-ROC on Unseen Target Center > 0.971 (vs Baseline: 0.823)",
            "Inference Throughput > 180 slices / sec (RTX 4090)"
        ],
        "hardware_requirements": {
            "GPU": "1x NVIDIA RTX 4090 (24GB VRAM) or A100 (40GB/80GB)",
            "CPU": "16 vCPUs (AMD EPYC / Intel Xeon)",
            "RAM": "64 GB System RAM",
            "expected_runtime": "3.2 hours across 60 epochs (batch size 32)",
            "precision": "Mixed Precision (AMP FP16)",
            "framework": "PyTorch 2.3+ with Timm, Hugging Face Transformers, CUDA 12.2",
            "storage": "80 GB SSD fast storage"
        },
        "ablation_matrix": [
            {"variant": "Standard ERM ViT (No GRL)", "purpose": "Standard empirical risk minimization without domain adaptation", "dice_expected": "77.4% OOD", "vram": "11.2 GB"},
            {"variant": "ResNet-50 + Heavy Augmentation", "purpose": "Tests whether classical color/spatial augmentations resolve scanner shift", "dice_expected": "74.2% OOD", "vram": "8.5 GB"},
            {"variant": "AdaBN (Adaptive BatchNorm)", "purpose": "Adapts batch statistics without adversarial feature alignment", "dice_expected": "83.1% OOD", "vram": "9.1 GB"},
            {"variant": "Proposed DA-ViT (Minimax GRL)", "purpose": "Full domain adversarial training with dynamic lambda scheduling", "dice_expected": "93.8% OOD", "vram": "13.6 GB"}
        ]
    },
    3: {
        "topic": "Graph Neural Network Drug Discovery for Alzheimer's Dynamic Protein Targets",
        "title": "Equivariant Temporal GNN with Dynamic Mode Decomposition for Intrinsically Disordered Alzheimer's Targets",
        "target_hypothesis": "Equivariant Temporal Graph Neural Network (ET-GNN) with Dynamic Mode Decomposition for Intrinsically Disordered Tau & Amyloid-beta Pockets",
        "target_gap": "GAP-01: Static Rigid Docking Failure on Intrinsically Disordered Conformations & Pocket Transience",
        "roadmap": [
            {
                "phase": "Phase 1",
                "step": "Phase 1: Dynamic Conformational Ensemble Extraction & Graph Encoding",
                "category": "Data Pipeline",
                "milestone": "Spatio-Temporal Pocket Graph Ensembles",
                "details": "Extract 5,316 refined protein-ligand complexes from PDBbind-CN v2020 and 1,513 small molecule inhibitors from MoleculeNet BACE-1. Retrieve solved Amyloid-beta and Tau Cryo-EM structural ensembles from RCSB PDB. Apply Dynamic Mode Decomposition (DMD) to short molecular dynamics trajectories to extract the top-5 dominant low-frequency conformational pocket states. Construct bipartite 3D graphs (G = (V, E, X)) containing atomic types, bond topologies, and temporal 3D coordinate displacement vectors within 10A of the binding pocket centroid.",
                "inputs": "PDBbind-CN v2020 Refined Set + MoleculeNet BACE1 + RCSB PDB Ensembles",
                "algorithm": "Dynamic Mode Decomposition (DMD) + 3D Bipartite Radius Graph Construction",
                "deliverables": "PyTorch Geometric temporal graph dataset (.pt shards) + pocket coordinate metadata",
                "mitigation": "Radius graph cutoff at 10A preserves essential allosteric interactions while capping graph node count under 250 atoms."
            },
            {
                "phase": "Phase 2",
                "step": "Phase 2: Equivariant Temporal Message Passing (ET-GNN) Architecture",
                "category": "Model Architecture",
                "milestone": "SE(3)-Equivariant Temporal GNN Network Compiled",
                "details": "Construct an SE(3)-equivariant Graph Neural Network with temporal attention layers. Node feature updates preserve 3D Euclidean rotation and translation equivariance via vector-valued message passing. Integrate a temporal attention aggregator across the 5 DMD conformational snapshots, enabling the network to learn which transient pocket geometries govern thermodynamic binding affinity.",
                "inputs": "Temporal 3D molecular graph sequences",
                "algorithm": "SE(3)-Equivariant Vector Message Passing + Temporal Self-Attention",
                "deliverables": "PyTorch Geometric ET-GNN module + equivariant unit tests",
                "mitigation": "Relative distance invariance ||x_i - x_j|| guarantees rotational and translational symmetry."
            },
            {
                "phase": "Phase 3",
                "step": "Phase 3: Multi-Task Binding Affinity & Kinetic Inhibition Training",
                "category": "Optimization Protocol",
                "milestone": "Joint Affinity & Inhibition Convergence",
                "details": "Train under a multi-task objective: L = L_MSE(-log Kd) + alpha * L_BCE(y_inhibit), with uncertainty weighting alpha. Use AdamW optimizer (lr=3e-4, weight decay 1e-5) with OneCycleLR scheduler. Execute on 80/10/10 scaffold-based split (Bemis-Murcko clustering) across 80 epochs with batch size 16 graph complexes.",
                "inputs": "Scaffold-partitioned molecular graph dataset",
                "algorithm": "Multi-Task MSE + BCE Loss with OneCycleLR & Gradient Clipping (norm=1.0)",
                "deliverables": "Best model checkpoint weights + predicted affinity correlation curves",
                "mitigation": "Bemis-Murcko scaffold splitting ensures the model cannot achieve artificially high scores via memorization of core chemical scaffolds."
            },
            {
                "phase": "Phase 4",
                "step": "Phase 4: Baseline Benchmarking on Dynamic IDP Targets",
                "category": "Ablation Studies",
                "milestone": "Dynamic Ensemble Superiority Confirmed",
                "details": "Benchmark ET-GNN against: (1) Static 2D GCN (Kipf & Welling); (2) Static 3D SchNet / EGNN; (3) Traditional AutoDock Vina rigid docking; (4) Full ET-GNN with DMD temporal attention. Quantify Pearson correlation (R), Spearman rank (rho), RMSE in -log Kd, and pocket hit rate on intrinsically disordered Tau hexapeptide motifs (PHF6).",
                "inputs": "Held-out scaffold test partition + RCSB PDB Tau/Abeta targets",
                "algorithm": "Cross-benchmark comparative evaluation under identical test splits",
                "deliverables": "Pearson/Spearman correlation tables + pocket ensemble coverage heatmaps",
                "mitigation": "Strict evaluation on experimentally confirmed binding assays (Kd/Ki) eliminates in-silico scoring bias."
            },
            {
                "phase": "Phase 5",
                "step": "Phase 5: Lead Candidate Virtual Screening & In-Silico ADMET Validation",
                "category": "Statistical Validation",
                "milestone": "Screening Pipeline Validated for Tau/Abeta Candidates",
                "details": "Screen 50,000 candidate compounds against the transient Tau/Abeta pocket ensemble. Filter hits by drug-likeness (Lipinski's Rule of 5, QED > 0.6) and predict blood-brain barrier (BBB) permeability. Validate screening enrichment factor (EF_1%) and compute 95% bootstrap confidence intervals for top lead candidate rankings.",
                "inputs": "ChEMBL library subset (50K molecules) + solved Tau/Amyloid fibrils",
                "algorithm": "Virtual Screening Pipeline + Pharmacokinetic ADMET Filter + Enrichment Analysis",
                "deliverables": "Top-20 candidate lead molecules report + predicted binding modes + BBB scores",
                "mitigation": "Falsification criterion: If Pearson R < 0.80 on scaffold test or EF1% < 8.0, the temporal hypothesis is rejected."
            }
        ],
        "metrics": [
            "Pearson Correlation (R) on Binding Affinity > 0.865 (vs Static 3D EGNN: 0.762 | Static 2D GCN: 0.684)",
            "Spearman Rank Correlation (rho) > 0.842 (vs Static EGNN: 0.738)",
            "Root Mean Squared Error (RMSE) < 1.18 -logKd units (vs Baseline: 1.54 units)",
            "Enrichment Factor at 1% (EF1%) > 14.5 (vs AutoDock Vina: 4.8)",
            "Pocket Ensemble Coverage > 88% on Disordered Tau Motifs (vs Rigid: 42%)",
            "Inference Latency < 12 ms / complex (vs MD simulation: > 48 hours)"
        ],
        "hardware_requirements": {
            "GPU": "1x NVIDIA RTX 4090 (24GB VRAM) or RTX 3090 (24GB VRAM)",
            "CPU": "12+ cores AMD Ryzen / Intel Core",
            "RAM": "64 GB System RAM",
            "expected_runtime": "2.2 hours across 80 epochs",
            "precision": "Mixed Precision (AMP FP16)",
            "framework": "PyTorch 2.3+ | PyTorch Geometric 2.5+ | RDKit | OpenMM",
            "storage": "50 GB SSD for graph tensors"
        },
        "ablation_matrix": [
            {"variant": "Static 2D GCN (Kipf & Welling)", "purpose": "Evaluates 2D molecular graph without 3D spatial conformation", "dice_expected": "R = 0.684", "vram": "4.8 GB"},
            {"variant": "Rigid 3D EGNN", "purpose": "Tests single static crystal structure without temporal dynamics", "dice_expected": "R = 0.762", "vram": "8.4 GB"},
            {"variant": "AutoDock Vina (Rigid Docking)", "purpose": "Classical empirical scoring function baseline", "dice_expected": "EF1% = 4.8", "vram": "CPU only"},
            {"variant": "Proposed ET-GNN (DMD Ensembles)", "purpose": "Full SE(3) equivariant temporal GNN over conformational ensembles", "dice_expected": "R > 0.865", "vram": "11.5 GB"}
        ]
    }
}

def refresh_all_plans():
    print("Starting Experiment Plans Refresh...")
    now = datetime.utcnow()

    for project_id, pdata in PLANS_BY_PROJECT.items():
        print(f"\nProcessing Project {project_id}: {pdata['topic']}")
        
        # 1. Clean existing plans for this project
        c.execute("DELETE FROM experiment_plans WHERE project_id=?", (project_id,))
        
        # Insert new experiment plan
        c.execute("""
            INSERT INTO experiment_plans (project_id, roadmap, metrics, hardware_requirements, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            project_id,
            json.dumps(pdata["roadmap"]),
            json.dumps(pdata["metrics"]),
            json.dumps(pdata["hardware_requirements"]),
            now
        ))
        plan_id = c.lastrowid
        print(f"  [OK] Inserted ExperimentPlan ID {plan_id}")

        # Update or insert knowledge node
        node_id = f"plan-{plan_id}"
        props = json.dumps({
            "title": pdata["title"],
            "target_hypothesis": pdata["target_hypothesis"],
            "target_gap": pdata["target_gap"],
            "total_phases": len(pdata["roadmap"]),
            "expected_runtime": pdata["hardware_requirements"].get("expected_runtime")
        })
        c.execute("""
            INSERT OR REPLACE INTO knowledge_nodes (id, project_id, type, label, properties)
            VALUES (?, ?, ?, ?, ?)
        """, (node_id, project_id, "experiment", f"Plan: {pdata['title'][:30]}", props))

        # 2. Update research_stage for 'planning'
        stage_output = {
            "plan_id": plan_id,
            "title": pdata["title"],
            "target_hypothesis": pdata["target_hypothesis"],
            "target_gap": pdata["target_gap"],
            "roadmap": pdata["roadmap"],
            "metrics": pdata["metrics"],
            "hardware_requirements": pdata["hardware_requirements"],
            "ablation_matrix": pdata["ablation_matrix"]
        }

        reasoning_chain = [
            {"step": 1, "thought": f"Synthesized research goals for '{pdata['topic']}' linking selected hypothesis '{pdata['target_hypothesis'][:50]}...' and '{pdata['target_gap']}'."},
            {"step": 2, "thought": f"Constructed 5 sequential, parameter-grounded experimental phases spanning data ingestion, baseline implementation, dual-objective optimization, ablation testing, and statistical generalization."},
            {"step": 3, "thought": "Defined quantitative target thresholds benchmarked against literature baselines and isolated key ablation experiments to test causal hypotheses."},
            {"step": 4, "thought": "Calculated realistic compute and memory budgets under PyTorch mixed precision (AMP FP16) to ensure reproducible execution within 24GB VRAM."}
        ]

        stage_row = c.execute("SELECT id FROM research_stages WHERE project_id=? AND stage_name='planning'", (project_id,)).fetchone()
        if stage_row:
            c.execute("""
                UPDATE research_stages
                SET status='completed', output_data=?, completed_at=?, is_approved=1, reasoning_chain=?
                WHERE id=?
            """, (
                json.dumps(stage_output),
                now,
                json.dumps(reasoning_chain),
                stage_row[0]
            ))
            print(f"  [OK] Updated research_stage 'planning' (ID {stage_row[0]}) to completed")
        else:
            c.execute("""
                INSERT INTO research_stages (project_id, stage_name, status, output_data, started_at, completed_at, is_approved, reasoning_chain)
                VALUES (?, 'planning', 'completed', ?, ?, ?, 1, ?)
            """, (
                project_id,
                json.dumps(stage_output),
                now,
                now,
                json.dumps(reasoning_chain)
            ))
            print(f"  [OK] Inserted new completed research_stage 'planning' for Project {project_id}")

    conn.commit()
    conn.close()
    print("\n[OK] Experiment Plans refresh complete for all projects!")

if __name__ == "__main__":
    refresh_all_plans()
