"use client";
import { useEffect, useState } from "react";
import { database } from "./firebase";
import { ref, onValue } from "firebase/database";

export default function Home() {
  const [detectionStatus, setDetectionStatus] = useState({
    motion_detected: false,
    humans_present: false,
    timestamp: null,
  });

  useEffect(() => {
    const statusRef = ref(database, "detection_status");
    onValue(statusRef, (snapshot) => {
      setDetectionStatus(snapshot.val() || {});
    });
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-col items-center justify-center w-full max-w-4xl px-6 py-20 space-y-10 sm:items-start sm:space-y-8">
        <h1 className="text-4xl font-semibold tracking-tight text-black dark:text-zinc-50">
          Motion Detector
        </h1>

        {/* Live Video Feed */}
        <div className="w-full aspect-video rounded-2xl overflow-hidden border border-zinc-300 dark:border-zinc-700 shadow-lg">
          <img
            src="http://localhost:5000/video_feed"
            alt="Live Feed"
            className="w-full h-full object-cover"
          />
        </div>

        {/* Detection Info */}
        <div className="w-full bg-white/70 dark:bg-zinc-900/50 backdrop-blur-md p-6 rounded-xl shadow-lg space-y-4">
          <p
            className={`text-lg font-medium ${
              detectionStatus.motion_detected
                ? "text-green-500"
                : "text-red-500"
            }`}
          >
            Motion Status:{" "}
            <span className="font-semibold">
              {detectionStatus.motion_detected ? "Detected" : "No Motion"}
            </span>
          </p>

          <p
            className={`text-lg font-medium ${
              detectionStatus.humans_present
                ? "text-green-500"
                : "text-red-500"
            }`}
          >
            Human Presence:{" "}
            <span className="font-semibold">
              {detectionStatus.humans_present ? "Detected" : "No Humans"}
            </span>
          </p>

          {detectionStatus.timestamp && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Last Updated:{" "}
              {new Date(detectionStatus.timestamp).toLocaleString()}
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
