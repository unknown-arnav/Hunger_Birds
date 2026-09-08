/// Backend base URL. Override at build/run time with:
///   flutter run --dart-define=API_BASE_URL=https://your-app.up.railway.app
class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );
}
