"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DriverMetricsPanel } from "@/components/DriverMetricsPanel";
import { DriverAlertBanner } from "@/components/DriverAlertBanner";
import { postDriverStreamFrame } from "@/lib/api";
import type { DriverStreamFrameResponse } from "@/types/api";

const FRAME_INTERVAL_MS = 100;
const CAPTURE_WIDTH = 640;
const CAPTURE_HEIGHT = 480;
const PERCLOS_ALERT_THRESHOLD = 25.0;

interface DriverFatiguePanelProps {
  truckId: string;
}

export function DriverFatiguePanel({ truckId }: DriverFatiguePanelProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inFlightRef = useRef(false);
  const calibrateNextRef = useRef(false);

  const [cameraError, setCameraError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [telemetry, setTelemetry] = useState<DriverStreamFrameResponse | null>(
    null
  );
  const [isCalibrating, setIsCalibrating] = useState(false);

  // Set up the webcam stream.
  useEffect(() => {
    let cancelled = false;

    async function setupCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError("Camera API not available in this browser/environment.");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: CAPTURE_WIDTH, height: CAPTURE_HEIGHT },
        });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => undefined);
        }
        setCameraReady(true);
        setCameraError(null);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.name === "NotAllowedError"
              ? "Camera permission denied. Allow camera access to enable driver fatigue monitoring."
              : err.name === "NotFoundError"
              ? "No camera device found on this machine."
              : err.message
            : "Unable to access the camera.";
        setCameraError(message);
        setCameraReady(false);
      }
    }

    void setupCamera();

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, []);

  // Frame capture + send loop.
  const sendFrame = useCallback(async () => {
    if (inFlightRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < video.HAVE_CURRENT_DATA) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, CAPTURE_WIDTH, CAPTURE_HEIGHT);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.5);

    const calibrate = calibrateNextRef.current;
    calibrateNextRef.current = false;

    inFlightRef.current = true;
    try {
      const response = await postDriverStreamFrame({
        image: dataUrl,
        equipment_id: truckId,
        calibrate,
      });
      setTelemetry(response);
    } catch {
      // Swallow transient network errors; keep the last good telemetry.
    } finally {
      inFlightRef.current = false;
    }
  }, [truckId]);

  useEffect(() => {
    if (!cameraReady) return;
    const id = setInterval(() => {
      void sendFrame();
    }, FRAME_INTERVAL_MS);
    return () => clearInterval(id);
  }, [cameraReady, sendFrame]);

  const handleCalibrate = useCallback(() => {
    calibrateNextRef.current = true;
    setIsCalibrating(true);
    setTimeout(() => setIsCalibrating(false), 1200);
  }, []);

  const perclos = telemetry?.perclos;
  const isDistracted = telemetry?.is_distracted ?? false;
  const showFatigueAlert =
    perclos !== undefined && perclos >= PERCLOS_ALERT_THRESHOLD;

  return (
    <div className="space-y-4">
      {/* Hidden capture elements */}
      <video ref={videoRef} className="hidden" muted playsInline />
      <canvas
        ref={canvasRef}
        width={CAPTURE_WIDTH}
        height={CAPTURE_HEIGHT}
        className="hidden"
      />

      {showFatigueAlert && (
        <DriverAlertBanner message="🚨 ВОДИТЕЛЬ ЗАСЫПАЕТ!" tone="red" />
      )}
      {isDistracted && (
        <DriverAlertBanner message="⚠️ ВЗГЛЯД ОТВЕДЕН!" tone="amber" />
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Live Feed</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCalibrate}
              disabled={!cameraReady || isCalibrating}
            >
              {isCalibrating ? "Calibrating..." : "Calibrate open eyes"}
            </Button>
          </CardHeader>
          <CardContent>
            {cameraError ? (
              <div className="flex aspect-[4/3] w-full items-center justify-center rounded-md border border-red-800 bg-red-950/30 p-4 text-center text-xs text-red-300">
                {cameraError}
              </div>
            ) : telemetry?.image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={telemetry.image}
                alt="Annotated driver camera frame"
                className="w-full rounded-md border border-slate-800"
              />
            ) : (
              <div className="flex aspect-[4/3] w-full items-center justify-center rounded-md border border-slate-800 bg-slate-900/50 text-xs text-slate-500">
                {cameraReady
                  ? "Waiting for first analyzed frame..."
                  : "Initializing camera..."}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Fatigue Metrics — {truckId}</CardTitle>
          </CardHeader>
          <CardContent>
            {telemetry?.success === false && telemetry.error ? (
              <div className="text-xs text-red-400">{telemetry.error}</div>
            ) : (
              <DriverMetricsPanel
                eyeState={telemetry?.state}
                isYawning={telemetry?.is_yawning}
                isDistracted={telemetry?.is_distracted}
                gazeLabel={telemetry?.gaze_label}
                smoothedEar={telemetry?.smoothed_ear}
                mar={telemetry?.mar}
                perclos={telemetry?.perclos}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
