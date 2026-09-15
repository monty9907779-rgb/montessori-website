"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import clsx from "clsx";

type RevealProps = {
  children: ReactNode;
  as?: "div" | "span" | "li";
  delay?: 1 | 2 | 3 | 4;
  className?: string;
};

export default function Reveal({ children, as = "div", delay, className }: RevealProps) {
  const ref = useRef<HTMLDivElement | HTMLSpanElement | HTMLLIElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -80px 0px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const Tag = as;

  return (
    <Tag
      ref={ref as never}
      className={clsx("reveal", visible && "is-visible", delay && `reveal-delay-${delay}`, className)}
    >
      {children}
    </Tag>
  );
}
