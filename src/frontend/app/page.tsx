"use client";

import { MeshGradient } from "@paper-design/shaders-react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, AudioLines, Mic, Plus } from "lucide-react";
import React, { JSX, useMemo, useState } from "react";
import useMeasure from "react-use-measure";

import { cn } from "@/utils/cn";

export default function Home() {
  const [ref, bounds] = useMeasure();
  const [inputValue, setInputValue] = useState("");
  const [isSubmit, setIsSubmit] = useState(false);

  const onSubmit = () => {
    setInputValue("");
    setIsSubmit(true);
  };

  return (
    <div className="perspective-near relative flex h-screen w-screen items-center justify-center px-3 text-[#121212]">
      <AnimatePresence mode="popLayout">
        {isSubmit ? (
          <motion.div
            key="output"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="absolute z-20 flex h-full w-full items-center justify-center text-center"
          >
            <TextShimmer className="text-lg" duration={1}>
              Generating Your $Billion Dollar saas...
            </TextShimmer>
          </motion.div>
        ) : (
          <motion.div
            key="input"
            exit={{ y: -100, opacity: 0, filter: "blur(4px)", rotateX: 25 }}
            animate={{ y: 0, opacity: 1, rotateX: 0 }}
            transition={{ duration: 0.3 }}
            layout
            className="z-2 absolute w-full max-w-sm rounded-3xl bg-white text-lg"
          >
            <div className="flex justify-between p-2">
              <div className="flex w-full items-center gap-1">
                <button className="absolute bottom-2 left-2 flex size-11 items-center justify-center rounded-full p-1">
                  <Plus className="text-muted-foreground size-5" />
                </button>
                <motion.div
                  className="w-full"
                  initial={false}
                  animate={{
                    paddingLeft: inputValue.length > 10 ? "15px" : "38px",
                    paddingRight: inputValue.length > 10 ? "15px" : "82px",
                    height: bounds.height || "auto",
                    marginBottom: inputValue.length > 10 ? "40px" : "0px",
                  }}
                >
                  <textarea
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        onSubmit();
                      }
                    }}
                    placeholder="Ask anything..."
                    ref={ref}
                    className={cn(
                      "field-sizing-content w-full resize-none rounded-md py-2 outline-0 focus-visible:ring-0",
                    )}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                  />
                </motion.div>
              </div>
              <div className="absolute bottom-2 right-2 flex">
                <button className="flex size-11 items-center justify-center rounded-full p-1">
                  <Mic className="size-5" />
                </button>

                {inputValue ? (
                  <motion.button
                    initial={{ scale: 0.5 }}
                    animate={{ scale: 1 }}
                    key="arrow-up"
                    className="flex size-11 items-center justify-center rounded-full bg-[#121212] p-1 text-white"
                  >
                    <ArrowUp className="size-5" />
                  </motion.button>
                ) : (
                  <motion.button
                    initial={{ scale: 0.5 }}
                    animate={{ scale: 1 }}
                    key="audio-lines"
                    className="flex size-11 items-center justify-center rounded-full bg-[#121212] p-1 text-white"
                  >
                    <AudioLines className="size-5" />
                  </motion.button>
                )}
              </div>
            </div>
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
