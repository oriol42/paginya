import type { Metadata } from "next";
import { VideoMaker } from "@/components/video/VideoMaker";

export const metadata: Metadata = { title: "Vidéos TikTok", robots: { index: false } };

export default function VideoPage() {
  return <VideoMaker />;
}
