/**
 * AFRAME stub for react-force-graph compatibility.
 * react-force-graph checks for window.AFRAME globally; we use 2D graphs only.
 */
(function () {
  if (typeof window !== 'undefined' && !window.AFRAME) {
    window.AFRAME = {
      registerComponent: function () {},
      registerSystem: function () {},
      registerPrimitive: function () {},
      scenes: [],
      version: '1.0.0',
    };
  }
})();
