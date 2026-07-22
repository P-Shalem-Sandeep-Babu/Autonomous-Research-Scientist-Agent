"use client";

import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from "chart.js";

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function ResearchChart({
  data,
  title = "Research Metrics",
}: {
  data: any;
  title?: string;
}) {
  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "top" as const,
      },
      title: {
        display: true,
        text: title,
        color: "#e2e8f0",
      },
    },
    scales: {
      x: {
        grid: {
          color: "rgba(34, 45, 68, 0.3)",
        },
        ticks: {
          color: "#e2e8f0",
        },
      },
      y: {
        grid: {
          color: "rgba(34, 45, 68, 0.3)",
        },
        ticks: {
          color: "#e2e8f0",
        },
      },
    },
  };

  return <Line options={options} data={data} />;
}