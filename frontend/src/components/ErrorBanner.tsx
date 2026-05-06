import { AlertCircle, X } from "lucide-react";

type ErrorBannerProps = {
  error: string | null;
  onClose: () => void;
  variant?: "error" | "warning" | "info";
};

export default function ErrorBanner({
  error,
  onClose,
  variant = "error",
}: ErrorBannerProps) {
  if (!error) return null;

  const bgColor =
    variant === "error"
      ? "bg-red-50 border-red-200"
      : variant === "warning"
        ? "bg-yellow-50 border-yellow-200"
        : "bg-blue-50 border-blue-200";

  const textColor =
    variant === "error"
      ? "text-red-800"
      : variant === "warning"
        ? "text-yellow-800"
        : "text-blue-800";

  const iconColor =
    variant === "error"
      ? "text-red-600"
      : variant === "warning"
        ? "text-yellow-600"
        : "text-blue-600";

  return (
    <div
      className={`fixed top-4 left-4 right-4 z-50 ${bgColor} border rounded-lg p-4 flex items-start gap-3 shadow-lg max-w-md`}
    >
      <AlertCircle className={`w-5 h-5 flex-shrink-0 ${iconColor}`} />
      <div className="flex-1">
        <p className={`${textColor} text-sm font-medium`}>{error}</p>
      </div>
      <button
        onClick={onClose}
        className="flex-shrink-0 text-gray-400 hover:text-gray-600"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
