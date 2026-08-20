export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] text-center">
      <h1 className="text-4xl font-bold tracking-tight mb-4">{title}</h1>
      <p className="text-muted-foreground max-w-md">
        This screen is part of the ChurnShield AI prototype. The primary focus of this demo is the Dashboard and the Rescue Agent flow.
      </p>
    </div>
  );
}