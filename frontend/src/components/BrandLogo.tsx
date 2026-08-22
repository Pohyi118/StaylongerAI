type BrandLogoProps = {
  alt?: string;
  className?: string;
};

export default function BrandLogo({
  alt = "StaylongerAI",
  className = "",
}: BrandLogoProps) {
  return (
    <img
      src="/staylonger-logo.png"
      alt={alt}
      decoding="async"
      className={`block object-contain ${className}`}
    />
  );
}
