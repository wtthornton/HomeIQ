/**
 * Preload THREE.js globally for react-force-graph.
 * Must run before any component that uses react-force-graph.
 */
import * as THREE from 'three';
if (typeof window !== 'undefined') {
  (window as unknown as { THREE: typeof THREE }).THREE = THREE;
}
