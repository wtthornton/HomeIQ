import { useState, useEffect } from 'react';

export interface AiTierInfo {
  label: string;
  color: string;
  description: string;
}

interface AiTierManifest {
  tiers: Record<string, AiTierInfo>;
  services: Record<string, string>;
}

let cachedManifest: AiTierManifest | null = null;

/**
 * Hook to load the AI tier manifest from public/ai-tier-manifest.json.
 * Cached after first load — the manifest is static and rarely changes.
 *
 * Epic 66, Story 66.5
 */
export function useAiTierManifest() {
  const [manifest, setManifest] = useState<AiTierManifest | null>(cachedManifest);

  useEffect(() => {
    if (cachedManifest) return;

    fetch('/ai-tier-manifest.json')
      .then((res) => res.json())
      .then((data: AiTierManifest) => {
        cachedManifest = data;
        setManifest(data);
      })
      .catch(() => {
        // Manifest is optional — badges just won't render
      });
  }, []);

  return manifest;
}

/**
 * Get the AI tier info for a service name.
 * Returns null if the manifest isn't loaded or the service isn't found.
 */
export function getServiceTier(
  manifest: AiTierManifest | null,
  serviceName: string
): (AiTierInfo & { tier: string }) | null {
  if (!manifest) return null;

  const tier = manifest.services[serviceName];
  if (!tier) return null;

  const info = manifest.tiers[tier];
  if (!info) return null;

  return { ...info, tier };
}
