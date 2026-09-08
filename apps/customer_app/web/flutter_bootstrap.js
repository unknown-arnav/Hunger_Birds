{{flutter_js}}
{{flutter_build_config}}

// Serve CanvasKit from our own build output instead of the gstatic CDN, so
// the web build still loads on networks where that CDN is slow or blocked.
_flutter.loader.load({
  config: { canvasKitBaseUrl: "canvaskit/" }
});
