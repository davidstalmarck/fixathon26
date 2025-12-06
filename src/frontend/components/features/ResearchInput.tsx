"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, AudioLines, Mic, Plus, Search, MessageSquare } from "lucide-react";
import React, { useState } from "react";
import useMeasure from "react-use-measure";

import { cn } from "@/utils/cn";

export type InputMode = "research" | "chat";

interface ResearchInputProps {
  mode: InputMode;
  onSubmit: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  minLength?: number;
}

export function ResearchInput({
  mode,
  onSubmit,
  placeholder = "Ask anything...",
  disabled = false,
  minLength = 10,
}: ResearchInputProps) {
  const [ref, bounds] = useMeasure();
  const [inputValue, setInputValue] = useState("");

  const handleSubmit = () => {
    if (disabled) return;
    if (mode === "research" && inputValue.length < minLength) return;
    if (inputValue.trim().length === 0) return;

    onSubmit(inputValue.trim());
    setInputValue("");
  };

  const isValid = mode === "chat" || inputValue.length >= minLength;

  return (
    <motion.div
      layout
      className="z-2 w-full max-w-sm rounded-3xl bg-white text-lg shadow-lg"
    >
      <div className="flex justify-between p-2">
        <div className="flex w-full items-center gap-1">
          <button className="absolute bottom-2 left-2 flex size-11 items-center justify-center rounded-full p-1">
            {mode === "research" ? (
              <Search className="text-muted-foreground size-5" />
            ) : (
              <MessageSquare className="text-muted-foreground size-5" />
            )}
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
                  handleSubmit();
                }
              }}
              placeholder={placeholder}
              ref={ref}
              className={cn(
                "field-sizing-content w-full resize-none rounded-md py-2 outline-0 focus-visible:ring-0",
                disabled && "opacity-50 cursor-not-allowed",
              )}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={disabled}
            />
          </motion.div>
        </div>
        <div className="absolute bottom-2 right-2 flex">
          <button className="flex size-11 items-center justify-center rounded-full p-1">
            <Mic className="size-5" />
          </button>

          <AnimatePresence mode="wait">
            {inputValue && isValid ? (
              <motion.button
                initial={{ scale: 0.5 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.5 }}
                key="submit"
                onClick={handleSubmit}
                disabled={disabled}
                className={cn(
                  "flex size-11 items-center justify-center rounded-full bg-[#121212] p-1 text-white",
                  disabled && "opacity-50 cursor-not-allowed",
                )}
              >
                <ArrowUp className="size-5" />
              </motion.button>
            ) : (
              <motion.button
                initial={{ scale: 0.5 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.5 }}
                key="audio-lines"
                className="flex size-11 items-center justify-center rounded-full bg-[#121212] p-1 text-white"
              >
                <AudioLines className="size-5" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </div>
      {mode === "research" && inputValue.length > 0 && inputValue.length < minLength && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="px-4 pb-2 text-xs text-orange-600"
        >
          Research queries need at least {minLength} characters ({inputValue.length}/{minLength})
        </motion.div>
      )}
    </motion.div>
  );
}
