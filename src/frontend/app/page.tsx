"use client";

import { MeshGradient } from "@paper-design/shaders-react";
import { AnimatePresence, motion } from "framer-motion";
import { Clock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { JSX, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ResearchInput, type InputMode } from "@/components/features/ResearchInput";
import { ModeToggle } from "@/components/ui/ModeToggle";
import { useCreateResearchRun } from "@/hooks/useResearchRun";
import { api } from "@/services/api";
import type { HasMoleculesResponse } from "@/types/molecule";
import { cn } from "@/utils/cn";

export default function Home() {
  const router = useRouter();
  const [mode, setMode] = useState<InputMode>("research");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if molecules exist for chat mode
  const { data: moleculesCheck } = useQuery({
    queryKey: ["molecules", "exists"],
    queryFn: () => api.get<HasMoleculesResponse>("/molecules"),
  });

  const hasMolecules = moleculesCheck?.hasMolecules ?? false;

  // Create research run mutation
  const createRun = useCreateResearchRun();

  const handleSubmit = async (value: string) => {
    if (mode === "research") {
      setIsSubmitting(true);
      try {
        const run = await createRun.mutateAsync({ query: value });
        router.push(`/results/${run.id}`);
      } catch (error) {
        setIsSubmitting(false);
        console.error("Failed to create research run:", error);
      }
    } else {
      // Chat mode - will be implemented in Phase 4
      console.log("Chat message:", value);
    }
  };

  return (
    <div className="perspective-near relative flex h-screen w-screen items-center justify-center px-3 text-[#121212]">
      {/* History icon */}
      <Link
        href="/history"
        className="absolute top-4 right-4 z-20 p-2 rounded-full bg-white/80 backdrop-blur hover:bg-white transition-colors"
        title="View history"
      >
        <Clock className="size-5 text-gray-600" />
      </Link>

      <AnimatePresence mode="popLayout">
        {isSubmitting ? (
          <motion.div
            key="output"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="absolute z-20 flex h-full w-full items-center justify-center text-center"
          >
            <TextShimmer className="text-lg" duration={1}>
              Searching scientific literature...
            </TextShimmer>
          </motion.div>
        ) : (
          <motion.div
            key="input"
            exit={{ y: -100, opacity: 0, filter: "blur(4px)", rotateX: 25 }}
            animate={{ y: 0, opacity: 1, rotateX: 0 }}
            transition={{ duration: 0.3 }}
            className="z-2 absolute flex flex-col items-center gap-4"
          >
            {/* Mode toggle */}
            <ModeToggle
              mode={mode}
              onModeChange={setMode}
              chatDisabled={!hasMolecules}
              chatDisabledReason="Run a research query first to enable chat"
            />

            {/* Input */}
            <ResearchInput
              mode={mode}
              onSubmit={handleSubmit}
              placeholder={
                mode === "research"
                  ? "Describe your research problem..."
                  : "Ask about discovered molecules..."
              }
              disabled={isSubmitting}
              minLength={10}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <MeshGradient
        speed={1}
        colors={["#C1DAFE", "#96BEFF", "#CFB7FC", "#EBE1F9"]}
        distortion={0.8}
        swirl={1}
        grainMixer={0}
        grainOverlay={0}
        style={{
          height: "100%",
          width: "100%",
          position: "absolute",
        }}
      />
    </div>
  );
}

// TextShimmer Component
export type TextShimmerProps = {
  children: string;
  as?: React.ElementType;
  className?: string;
  duration?: number;
  spread?: number;
};

function TextShimmerComponent({
  children,
  as: Component = "p",
  className,
  duration = 2,
  spread = 2,
}: TextShimmerProps) {
  const MotionComponent = motion.create(
    Component as keyof JSX.IntrinsicElements,
  );

  const dynamicSpread = useMemo(() => {
    return children.length * spread;
  }, [children, spread]);

  return (
    <MotionComponent
      className={cn(
        "relative inline-block bg-[length:250%_100%,auto] bg-clip-text",
        "text-transparent [--base-color:#a1a1aa] [--base-gradient-color:#000]",
        "[--bg:linear-gradient(90deg,#0000_calc(50%-var(--spread)),var(--base-gradient-color),#0000_calc(50%+var(--spread)))] [background-repeat:no-repeat,padding-box]",
        "dark:[--base-color:#71717a] dark:[--base-gradient-color:#ffffff] dark:[--bg:linear-gradient(90deg,#0000_calc(50%-var(--spread)),var(--base-gradient-color),#0000_calc(50%+var(--spread)))]",
        className,
      )}
      initial={{ backgroundPosition: "100% center" }}
      animate={{ backgroundPosition: "0% center" }}
      transition={{
        repeat: Infinity,
        duration,
        ease: "linear",
      }}
      style={
        {
          "--spread": `${dynamicSpread}px`,
          backgroundImage: `var(--bg), linear-gradient(var(--base-color), var(--base-color))`,
        } as React.CSSProperties
      }
    >
      {children}
    </MotionComponent>
  );
}

export const TextShimmer = React.memo(TextShimmerComponent);
