# Mobile app

Reserved for the Phase 1B mobile client. Phase 1A exposes the backend contract only.

# Lingua Mobile — Phase 1C

Flutter/Dart mobile client for the Phase 1A FastAPI service. The app uses Riverpod for state, GoRouter for navigation, Dio for HTTP, a shared blue-white design system, and a small dependency-free EN/MM localization layer.

## Setup

Install Flutter 3.22+ with Dart 3.3+, then run:

```bash
flutter pub get
flutter analyze
flutter test
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

`API_BASE_URL` defaults to `http://localhost:8000` and is read with `String.fromEnvironment`.

### API URL by target

- Android emulator: `http://10.0.2.2:8000`
- iOS simulator: `http://localhost:8000`
- Physical Android/iOS device: use the development machine’s LAN hostname or IP, for example `http://192.168.1.20:8000`, with the API bound to an accessible interface.

For older macOS/Xcode installations, use a Flutter SDK compatible with the installed Xcode and iOS deployment target. If CocoaPods reports a deployment-target or architecture issue, update the Podfile target only to the maximum supported by that Xcode, run `pod repo update`/`pod install`, and avoid upgrading Xcode-dependent packages blindly. Device signing, simulator builds, and native platform files were not verifiable in this environment because Flutter/Dart are not installed.

## Phase 1C scope

Text translation, language loading, capabilities loading, theme switching, and EN/MM switching are implemented. Voice, Camera, OCR, Documents, auth, persistence, and provider integrations are intentionally unavailable and are never simulated. A backend `503 TRANSLATION_ENGINE_NOT_CONFIGURED` response is shown as an actionable error and no invented result is displayed.
