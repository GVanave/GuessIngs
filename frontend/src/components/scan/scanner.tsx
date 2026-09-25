"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, ImageUp, Keyboard, Lightbulb, RotateCcw, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Extraction } from "@/lib/types";
import { validateImageFile } from "@/lib/validation";
import { cn } from "@/lib/utils";
import { AnalyzeForm } from "@/components/analysis/analyze-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Step =
  | { name: "choose" }
  | { name: "camera" }
  | { name: "extracting"; preview: string }
  | { name: "review"; preview: string; extraction: Extraction; source: "camera" | "upload" }
  | { name: "error"; preview?: string; message: string; code: string; tips: string[] };

const PROGRESS = ["Uploading photo…", "Reading the label…", "Extracting ingredients…"];

const TIPS = [
  "Fill the frame with the ingredients panel.",
  "Use good, even lighting and avoid glare.",
  "Hold steady and tap to focus before capturing.",
];

export function Scanner() {
  const [step, setStep] = useState<Step>({ name: "choose" });
  const [progress, setProgress] = useState(0);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const captureRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const previewRef = useRef<string | null>(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => () => {
    stopCamera();
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
  }, [stopCamera]);

  useEffect(() => {
    if (step.name !== "extracting") return;
    setProgress(0);
    const id = setInterval(() => setProgress((p) => Math.min(p + 1, PROGRESS.length - 1)), 1400);
    return () => clearInterval(id);
  }, [step.name]);

  async function extract(blob: Blob, source: "camera" | "upload", filename: string) {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    const preview = URL.createObjectURL(blob);
    previewRef.current = preview;
    setStep({ name: "extracting", preview });
    try {
      const extraction = await api.extract(blob, filename);
      setStep({ name: "review", preview, extraction, source });
    } catch (err) {
      const e = err instanceof ApiError ? err : new ApiError(0, "unknown", "Something went wrong. Please try again.");
      const tips = Array.isArray(e.details?.tips) ? (e.details!.tips as string[]) : [];
      setStep({ name: "error", preview, message: e.message, code: e.code, tips });
    }
  }

  function onFile(file: File | undefined, source: "camera" | "upload") {
    if (!file) return;
    const problem = validateImageFile(file);
    if (problem) {
      setStep({ name: "error", message: problem, code: "invalid_file", tips: [] });
      return;
    }
    void extract(file, source, file.name || "label.jpg");
  }

  async function startCamera() {
    setCameraError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      captureRef.current?.click(); // Fall back to the native camera picker.
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      setStep({ name: "camera" });
      requestAnimationFrame(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play().catch(() => undefined);
        }
      });
    } catch (err) {
      const denied = err instanceof DOMException && (err.name === "NotAllowedError" || err.name === "SecurityError");
      setCameraError(
        denied
          ? "Camera access was blocked. Allow camera access in your browser settings, or upload a photo instead."
          : "We couldn't start the camera on this device. Upload a photo instead.",
      );
    }
  }

  function capture() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        stopCamera();
        if (blob) void extract(blob, "camera", "camera.jpg");
      },
      "image/jpeg",
      0.92,
    );
  }

  function reset() {
    stopCamera();
    setStep({ name: "choose" });
  }

  const hiddenInputs = (
    <>
      <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" tabIndex={-1} aria-hidden
        data-testid="file-input" onChange={(e) => { onFile(e.target.files?.[0], "upload"); e.target.value = ""; }} />
      <input ref={captureRef} type="file" accept="image/*" capture="environment" className="sr-only" tabIndex={-1} aria-hidden
        onChange={(e) => { onFile(e.target.files?.[0], "camera"); e.target.value = ""; }} />
    </>
  );

  if (step.name === "camera") {
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-black" role="dialog" aria-modal="true" aria-label="Camera">
        <video ref={videoRef} playsInline muted className="h-full w-full flex-1 object-cover" />
        <div aria-hidden className="pointer-events-none absolute inset-x-6 top-1/2 h-[46%] -translate-y-1/2 rounded-3xl border-2 border-white/80 shadow-[0_0_0_9999px_rgba(0,0,0,0.45)]" />
        <p className="absolute inset-x-0 top-6 text-center text-sm font-medium text-white">Fit the ingredient list inside the frame</p>
        <div className="safe-bottom absolute inset-x-0 bottom-0 flex items-center justify-around pb-8">
          <Button variant="ghost" size="icon" onClick={reset} aria-label="Close camera" className="text-white hover:bg-white/10">
            <X className="size-6" />
          </Button>
          <button
            type="button"
            onClick={capture}
            aria-label="Take photo"
            className="grid size-20 place-items-center rounded-full border-4 border-white bg-white/20 transition-transform active:scale-95"
          >
            <span className="size-14 rounded-full bg-white" />
          </button>
          <Button variant="ghost" size="icon" onClick={() => { stopCamera(); setStep({ name: "choose" }); fileRef.current?.click(); }}
            aria-label="Upload a photo instead" className="text-white hover:bg-white/10">
            <ImageUp className="size-6" />
          </Button>
        </div>
        {hiddenInputs}
      </div>
    );
  }

  if (step.name === "extracting") {
    return (
      <Card className="mx-auto max-w-lg overflow-hidden" aria-busy="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={step.preview} alt="Photo being analyzed" className="h-56 w-full object-cover opacity-80" />
        <CardContent className="pt-6" role="status" aria-live="polite">
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
            <div className="h-full rounded-full bg-primary transition-all duration-700" style={{ width: `${((progress + 1) / PROGRESS.length) * 90}%` }} />
          </div>
          <p className="mt-4 text-center font-medium">{PROGRESS[progress]}</p>
          <p className="mt-1 text-center text-sm text-muted">This usually takes a few seconds.</p>
        </CardContent>
      </Card>
    );
  }

  if (step.name === "review") {
    const { extraction: x } = step;
    return (
      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <div className="space-y-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={step.preview} alt="Your label photo" className="max-h-72 w-full rounded-2xl border border-border bg-surface-2 object-contain lg:max-h-none" />
          <p className="text-xs text-muted">
            {x.ai_used ? "Read with AI-assisted OCR." : `Read with OCR (confidence ${Math.round(x.ocr_confidence)}%).`} Please check
            the text before analyzing.
          </p>
          {x.quality_warnings.length > 0 && (
            <Alert tone="warn" title="Photo quality">
              <ul>{x.quality_warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </Alert>
          )}
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Review extracted ingredients</CardTitle>
          </CardHeader>
          <CardContent>
            <AnalyzeForm
              source={step.source}
              ocrText={x.ocr_text}
              initial={{
                ingredients_text: x.ingredients_text,
                product_name: x.product_name ?? "",
                brand: x.brand ?? "",
                sodium: x.sodium_mg_per_100g != null ? String(Math.round(x.sodium_mg_per_100g)) : "",
              }}
              onCancel={reset}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {step.name === "error" && (
        <Alert
          tone="error"
          title={step.code === "low_quality_image" ? "The photo is hard to read" : step.code === "network_error" ? "Connection problem" : "We couldn't read that label"}
          action={
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={startCamera}><RotateCcw /> Retake photo</Button>
              <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()}><ImageUp /> Upload another</Button>
              <Button asChild size="sm" variant="ghost"><Link href="/analyze"><Keyboard /> Type instead</Link></Button>
            </div>
          }
        >
          <p>{step.message}</p>
          {step.tips.length > 0 && <ul className="mt-1 list-inside list-disc">{step.tips.map((t) => <li key={t}>{t}</li>)}</ul>}
        </Alert>
      )}
      {cameraError && <Alert tone="warn" title="Camera unavailable">{cameraError}</Alert>}

      <div
        className={cn("grid gap-4 sm:grid-cols-2", dragging && "rounded-3xl ring-2 ring-ring ring-offset-4 ring-offset-background")}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); onFile(e.dataTransfer.files?.[0], "upload"); }}
      >
        <button
          type="button"
          onClick={startCamera}
          className="group flex min-h-48 flex-col items-start justify-between rounded-3xl bg-primary p-6 text-left text-primary-foreground shadow-card transition-transform active:scale-[0.99]"
        >
          <span className="grid size-12 place-items-center rounded-2xl bg-white/15"><Camera className="size-6" aria-hidden /></span>
          <span>
            <span className="block text-xl font-semibold">Scan with camera</span>
            <span className="mt-1 block text-sm opacity-80">Point at the ingredients panel</span>
          </span>
        </button>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="flex min-h-48 flex-col items-start justify-between rounded-3xl border-2 border-dashed border-border bg-surface p-6 text-left transition-colors hover:border-ring hover:bg-surface-2"
        >
          <span className="grid size-12 place-items-center rounded-2xl bg-surface-2"><ImageUp className="size-6" aria-hidden /></span>
          <span>
            <span className="block text-xl font-semibold">Upload a photo</span>
            <span className="mt-1 block text-sm text-muted">JPG, PNG or WEBP up to 8 MB · or drop it here</span>
          </span>
        </button>
      </div>

      <Link href="/analyze" className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-4 transition-colors hover:bg-surface-2">
        <span className="grid size-10 place-items-center rounded-xl bg-surface-2"><Keyboard className="size-5" aria-hidden /></span>
        <span className="flex-1">
          <span className="block font-semibold">Type ingredients instead</span>
          <span className="block text-sm text-muted">Paste or type the list manually</span>
        </span>
      </Link>

      <div className="rounded-2xl bg-surface-2/70 p-5">
        <p className="flex items-center gap-2 text-sm font-semibold"><Lightbulb className="size-4 text-warn" aria-hidden /> Tips for a great scan</p>
        <ul className="mt-2 space-y-1 text-sm text-muted">{TIPS.map((t) => <li key={t}>• {t}</li>)}</ul>
      </div>
      {hiddenInputs}
    </div>
  );
}
