import Image from "next/image";
import { ImageOff } from "lucide-react";
import clsx from "clsx";

type PhotoFrameProps = {
  src?: string;
  alt: string;
  comingSoonLabel: string;
  className?: string;
  aspect?: "square" | "video" | "portrait";
  sizes?: string;
  priority?: boolean;
};

const ASPECT_CLASS: Record<NonNullable<PhotoFrameProps["aspect"]>, string> = {
  square: "aspect-square",
  video: "aspect-video",
  portrait: "aspect-[3/4]",
};

export default function PhotoFrame({
  src,
  alt,
  comingSoonLabel,
  className,
  aspect = "square",
  sizes = "(min-width: 1024px) 33vw, 50vw",
  priority = false,
}: PhotoFrameProps) {
  return (
    <div
      className={clsx(
        "relative overflow-hidden rounded-3xl surface-warm",
        ASPECT_CLASS[aspect],
        className
      )}
    >
      {src ? (
        <Image
          src={src}
          alt={alt}
          fill
          sizes={sizes}
          priority={priority}
          className="object-cover"
        />
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-primary-600">
          <ImageOff size={28} className="opacity-60" aria-hidden="true" />
          <span className="text-sm font-semibold">{comingSoonLabel}</span>
        </div>
      )}
    </div>
  );
}
