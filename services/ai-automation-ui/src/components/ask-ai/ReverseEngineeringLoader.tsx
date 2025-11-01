/**
 * Reverse Engineering Loader - Modern & Bold Loading Component
 * 
 * Displays a sleek, tech-focused loading experience while reverse engineering
 * validates and improves the automation YAML.
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { createPortal } from 'react-dom';

interface ReverseEngineeringLoaderProps {
  isVisible: boolean;
  iteration?: number;
  similarity?: number;
}

const TECH_MESSAGES = [
  {
    text: "Processing automation logic with neural networks...",
    icon: "⚡",
    color: "from-blue-500 to-cyan-500"
  },
  {
    text: "Reverse engineering YAML structure... (totally legal, we promise!)",
    icon: "🔧",
    color: "from-gray-600 to-gray-800"
  },
  {
    text: "Optimizing automation efficiency... because slow is the new broken",
    icon: "⚙️",
    color: "from-indigo-600 to-purple-600"
  },
  {
    text: "Validating entity mappings... finding your smart home's soul",
    icon: "🔍",
    color: "from-slate-700 to-slate-900"
  },
  {
    text: "Calculating semantic similarity metrics... AI doing math so you don't have to",
    icon: "📊",
    color: "from-blue-600 to-indigo-700"
  },
  {
    text: "Refining automation architecture... building the future, one trigger at a time",
    icon: "🏗️",
    color: "from-gray-700 to-gray-900"
  },
  {
    text: "Analyzing execution patterns... predicting the unpredictable",
    icon: "💻",
    color: "from-cyan-600 to-blue-700"
  },
  {
    text: "Optimizing performance parameters... because speed matters (especially when coffee's involved)",
    icon: "🚀",
    color: "from-indigo-700 to-blue-800"
  },
  {
    text: "Validating safety constraints... keeping your home safe from rogue automations",
    icon: "🛡️",
    color: "from-emerald-600 to-teal-700"
  },
  {
    text: "Finalizing automation configuration... dotting i's and crossing t's",
    icon: "✅",
    color: "from-gray-800 to-slate-900"
  },
  {
    text: "Teaching robots to understand your intentions... we're basically AI therapists now",
    icon: "🧠",
    color: "from-purple-600 to-pink-600"
  },
  {
    text: "Compiling your wishes into YAML... it's like poetry, but with indentation",
    icon: "📝",
    color: "from-blue-500 to-indigo-600"
  },
  {
    text: "Running quality assurance checks... making sure nothing explodes (metaphorically)",
    icon: "🔬",
    color: "from-cyan-600 to-teal-700"
  },
  {
    text: "Cross-referencing entity databases... playing matchmaker for your devices",
    icon: "💕",
    color: "from-pink-600 to-rose-600"
  },
  {
    text: "Performing semantic analysis... because context is everything",
    icon: "🎯",
    color: "from-orange-600 to-red-600"
  },
  {
    text: "Enhancing automation intelligence... adding IQ points to your smart home",
    icon: "🧬",
    color: "from-emerald-600 to-green-700"
  },
  {
    text: "Running pattern recognition algorithms... finding order in chaos",
    icon: "🌀",
    color: "from-violet-600 to-purple-700"
  },
  {
    text: "Optimizing trigger conditions... because timing is everything",
    icon: "⏱️",
    color: "from-yellow-600 to-orange-600"
  },
  {
    text: "Validating device compatibility... making sure your lights aren't feeling left out",
    icon: "🔌",
    color: "from-blue-600 to-cyan-700"
  },
  {
    text: "Applying machine learning magic... abracadabra meets algorithm",
    icon: "✨",
    color: "from-indigo-600 to-purple-700"
  },
  {
    text: "Calibrating automation precision... hitting the target every single time",
    icon: "🎯",
    color: "from-red-600 to-orange-700"
  },
  {
    text: "Synchronizing device states... getting everything on the same page",
    icon: "🔄",
    color: "from-cyan-500 to-blue-600"
  },
  {
    text: "Building execution pipelines... because automation is an art form",
    icon: "🏭",
    color: "from-gray-600 to-slate-800"
  },
  {
    text: "Cross-validating trigger logic... ensuring rock-solid reliability",
    icon: "🔐",
    color: "from-emerald-700 to-green-800"
  },
  {
    text: "Executing predictive modeling... seeing into the automation future",
    icon: "🔮",
    color: "from-purple-700 to-indigo-800"
  },
  {
    text: "Fine-tuning automation parameters... precision engineering at work",
    icon: "⚙️",
    color: "from-blue-700 to-cyan-800"
  },
  {
    text: "Optimizing resource allocation... maximum efficiency, zero waste",
    icon: "💎",
    color: "from-indigo-800 to-purple-900"
  },
  {
    text: "Establishing execution protocols... setting the automation standard",
    icon: "📋",
    color: "from-slate-700 to-gray-900"
  },
  {
    text: "Harmonizing device interactions... making your home sing in perfect sync",
    icon: "🎵",
    color: "from-pink-700 to-rose-800"
  },
  {
    text: "Forging automation pathways... creating connections that actually make sense",
    icon: "⚒️",
    color: "from-orange-700 to-red-800"
  },
  {
    text: "Reinforcing automation integrity... bulletproofing your smart home setup",
    icon: "🛠️",
    color: "from-gray-800 to-slate-900"
  },
  {
    text: "Amplifying automation performance... turning good into exceptional",
    icon: "📈",
    color: "from-green-700 to-emerald-800"
  },
  {
    text: "Constructing execution frameworks... the architecture behind the magic",
    icon: "🏛️",
    color: "from-blue-800 to-indigo-900"
  },
  {
    text: "Mastering automation orchestration... conducting the smart home symphony",
    icon: "🎼",
    color: "from-purple-800 to-violet-900"
  },
  {
    text: "Elevating automation intelligence... leveling up your home's IQ",
    icon: "🧠",
    color: "from-cyan-700 to-blue-800"
  },
  {
    text: "Polishing automation edges... smooth operator in the making",
    icon: "💎",
    color: "from-indigo-900 to-purple-950"
  },
  {
    text: "Crafting execution strategies... tactical automation deployment",
    icon: "🗺️",
    color: "from-teal-700 to-cyan-800"
  },
  {
    text: "Maximizing automation potential... unlocking peak performance",
    icon: "🔓",
    color: "from-emerald-800 to-green-900"
  },
  {
    text: "Engineering automation excellence... precision meets power",
    icon: "⚡",
    color: "from-yellow-700 to-orange-800"
  },
  {
    text: "Perfecting automation execution... because almost perfect isn't good enough",
    icon: "✨",
    color: "from-cyan-800 to-blue-900"
  },
  {
    text: "Optimizing automation dynamics... finding the perfect balance",
    icon: "⚖️",
    color: "from-slate-800 to-gray-950"
  }
];

const TECH_TIPS = [
  "💡 Using advanced semantic analysis to match user intent",
  "💡 Reverse engineering ensures 95%+ accuracy in automation generation",
  "💡 Multi-iteration refinement for optimal performance",
  "💡 Real-time validation prevents execution failures",
  "💡 Entity resolution uses machine learning models",
  "💡 Similarity matching compares meaning, not just syntax",
  "💡 Did you know? This AI has read more YAML than most developers",
  "💡 Fun fact: We're basically teaching robots to read your mind",
  "💡 Pro tip: The longer the wait, the better the automation (trust us)",
  "💡 While you wait: Your automation is getting smarter by the second",
  "💡 Behind the scenes: Multiple AI models are collaborating on this",
  "💡 Fun fact: This process uses enough compute to power a small city (okay, maybe a house)",
  "💡 Pro tip: Perfect automations take time - like fine wine or good code",
  "💡 Did you know? We're comparing your request to thousands of automations",
  "💡 While you wait: The AI is double-checking every semicolon and indent",
  "💡 Fun fact: Your automation is being refined in real-time as we speak",
  "💡 Pro tip: The reverse engineering process learns from every automation it sees",
  "💡 Did you know? This is more advanced than most enterprise automation tools",
  "💡 While you wait: Consider what other automations you'd like to create next",
  "💡 Fun fact: We're optimizing for both accuracy AND your sanity"
];

const PROGRESS_STAGES = [
  { step: 0, text: "Initializing", icon: "⚡" },
  { step: 1, text: "Analyzing", icon: "🔍" },
  { step: 2, text: "Processing", icon: "⚙️" },
  { step: 3, text: "Refining", icon: "🔧" },
  { step: 4, text: "Validating", icon: "✅" },
  { step: 5, text: "Finalizing", icon: "🚀" }
];

const TITLE_VARIATIONS = [
  "OPTIMIZING AUTOMATION",
  "ENGINEERING EXCELLENCE",
  "PERFECTING YOUR SETUP",
  "REFINING INTELLIGENCE",
  "BUILDING THE FUTURE",
  "CALIBRATING PRECISION",
  "SYNCHRONIZING SYSTEMS",
  "ORCHESTRATING MASTERY",
  "AMPLIFYING PERFORMANCE",
  "ELEVATING INTELLIGENCE",
  "FORGING PERFECTION",
  "POLISHING AUTOMATION",
  "MAXIMIZING POTENTIAL",
  "ENHANCING CAPABILITIES",
  "STREAMLINING EXECUTION",
  "POWERING UP",
  "TUNING FOR SUCCESS",
  "MASTERING THE CRAFT",
  "REFINING EXECUTION",
  "OPTIMIZING PERFORMANCE"
];

export const ReverseEngineeringLoader: React.FC<ReverseEngineeringLoaderProps> = ({
  isVisible,
  iteration = 0,
  similarity = 0
}) => {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [currentTitleIndex, setCurrentTitleIndex] = useState(0);
  const [pulseActive, setPulseActive] = useState(true);

  // Reset all indices when visibility changes to false (prevent stacking)
  useEffect(() => {
    if (!isVisible) {
      setCurrentMessageIndex(0);
      setCurrentTipIndex(0);
      setCurrentTitleIndex(0);
      setPulseActive(true);
    }
  }, [isVisible]);

  // Rotate messages every 2.5 seconds
  useEffect(() => {
    if (!isVisible) return;

    const messageInterval = setInterval(() => {
      setCurrentMessageIndex((prev) => (prev + 1) % TECH_MESSAGES.length);
    }, 2500);

    return () => clearInterval(messageInterval);
  }, [isVisible]);

  // Rotate title every 3 seconds
  useEffect(() => {
    if (!isVisible) return;

    const titleInterval = setInterval(() => {
      setCurrentTitleIndex((prev) => (prev + 1) % TITLE_VARIATIONS.length);
    }, 3000);

    return () => clearInterval(titleInterval);
  }, [isVisible]);

  // Rotate tips every 4 seconds
  useEffect(() => {
    if (!isVisible) return;

    const tipInterval = setInterval(() => {
      setCurrentTipIndex((prev) => (prev + 1) % TECH_TIPS.length);
    }, 4000);

    return () => clearInterval(tipInterval);
  }, [isVisible]);

  // Pulse effect
  useEffect(() => {
    if (!isVisible) return;

    const pulseInterval = setInterval(() => {
      setPulseActive((prev) => !prev);
    }, 2000);

    return () => clearInterval(pulseInterval);
  }, [isVisible]);

  const currentMessage = TECH_MESSAGES[currentMessageIndex];
  const currentTip = TECH_TIPS[currentTipIndex];
  const progressStep = Math.min(iteration || 0, 5);
  const progressStage = PROGRESS_STAGES[progressStep] || PROGRESS_STAGES[0];

  if (!isVisible) {
    return null;
  }

  const loaderContent = (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 999999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)'
      }}
    >
      {/* Animated grid background */}
      <div className="absolute inset-0 opacity-10" style={{
        backgroundImage: `
          linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px),
          linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px',
        animation: 'gridMove 20s linear infinite'
      }} />

      {/* Main card */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className="relative bg-gradient-to-br from-slate-900 via-slate-800 to-gray-900 rounded-xl shadow-2xl p-10 max-w-lg mx-4 text-center border border-slate-700/50"
        style={{
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(59, 130, 246, 0.2), 0 0 100px rgba(59, 130, 246, 0.1)',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)'
        }}
      >
        {/* Corner accent lines */}
        <div className="absolute top-0 left-0 w-20 h-20 border-t-2 border-l-2 border-blue-500/50" />
        <div className="absolute top-0 right-0 w-20 h-20 border-t-2 border-r-2 border-blue-500/50" />
        <div className="absolute bottom-0 left-0 w-20 h-20 border-b-2 border-l-2 border-blue-500/50" />
        <div className="absolute bottom-0 right-0 w-20 h-20 border-b-2 border-r-2 border-blue-500/50" />

        {/* Central icon with glow */}
        <div className="relative mb-6 flex justify-center">
          <motion.div
            animate={{
              scale: pulseActive ? [1, 1.1, 1] : 1,
              rotate: [0, 5, -5, 0],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="text-6xl mb-2 relative"
          >
            {progressStage.icon}
            <motion.div
              className="absolute inset-0 blur-xl opacity-50"
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.3, 0.6, 0.3]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              {progressStage.icon}
            </motion.div>
          </motion.div>
        </div>

        {/* Title */}
        <AnimatePresence mode="wait">
          <motion.h2
            key={currentTitleIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="text-2xl font-bold mb-3 bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent tracking-tight"
          >
            {TITLE_VARIATIONS[currentTitleIndex]}
          </motion.h2>
        </AnimatePresence>

        {/* Current message - wrapped in AnimatePresence for proper exit */}
        <div className="min-h-[3rem] mb-6 flex items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.p
              key={currentMessageIndex}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="text-sm text-slate-300 font-medium text-center"
            >
              {currentMessage.text}
            </motion.p>
          </AnimatePresence>
        </div>

        {/* Progress indicator */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {progressStage.icon} {progressStage.text}
            </span>
            {iteration > 0 && (
              <span className="text-xs font-bold text-blue-400">
                ITERATION {iteration}/5
              </span>
            )}
          </div>
          
          {/* Modern progress bar */}
          <div className="relative w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
            <motion.div
              className={`h-full bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-600 rounded-full`}
              initial={{ width: 0 }}
              animate={{ width: `${Math.min((iteration * 20) + (similarity * 20), 100)}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            >
              {/* Shimmer effect */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                animate={{
                  x: ['-100%', '100%'],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "linear"
                }}
              />
            </motion.div>
          </div>

          {similarity > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center mt-3"
            >
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                ✦ {Math.round(similarity * 100)}% QUALITY MATCH
              </span>
            </motion.div>
          )}
        </div>

        {/* Tech loading indicator */}
        <div className="flex items-center justify-center mb-6">
          <div className="flex space-x-2">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-2 h-8 bg-blue-500 rounded-full"
                animate={{
                  scaleY: [1, 1.5, 1],
                  opacity: [0.5, 1, 0.5],
                }}
                transition={{
                  duration: 1,
                  repeat: Infinity,
                  delay: i * 0.2,
                  ease: "easeInOut"
                }}
              />
            ))}
          </div>
          <motion.span
            animate={{ opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="ml-4 text-xs font-semibold text-slate-400 uppercase tracking-wider"
          >
            PROCESSING
          </motion.span>
        </div>

        {/* Tech tip - wrapped in AnimatePresence for proper exit */}
        <div className="min-h-[4rem]">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentTipIndex}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/30 backdrop-blur-sm"
            >
              <p className="text-xs text-slate-400 leading-relaxed">
                {currentTip}
              </p>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Bottom accent */}
        <div className="mt-6 text-xs text-slate-500 font-medium uppercase tracking-wider">
          <motion.span
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            STAND BY FOR COMPLETION
          </motion.span>
        </div>

        {/* Animated corner elements */}
        <div className="absolute -top-2 -right-2 w-4 h-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="w-full h-full border-2 border-blue-500/50 border-t-blue-500"
          />
        </div>
        <div className="absolute -bottom-2 -left-2 w-4 h-4">
          <motion.div
            animate={{ rotate: -360 }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="w-full h-full border-2 border-cyan-500/50 border-b-cyan-500"
          />
        </div>
      </motion.div>

      {/* Add CSS for grid animation */}
      <style>{`
        @keyframes gridMove {
          0% { transform: translate(0, 0); }
          100% { transform: translate(50px, 50px); }
        }
      `}</style>
    </div>
  );

  // Use portal to render at document root for maximum z-index
  if (typeof document === 'undefined' || !document.body) {
    return loaderContent;
  }

  try {
    return createPortal(loaderContent, document.body);
  } catch (error) {
    console.error('❌ Portal creation failed:', error);
    return loaderContent;
  }
};
