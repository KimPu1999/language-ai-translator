# Lingua Mobile — Phase 2D

Flutter/Dart mobile client for the FastAPI service. The app uses Riverpod for state, GoRouter for navigation, Dio for HTTP, Material 3, SharedPreferences for explicit local saves, a shared blue-white design system, and a small dependency-free EN/MM localization layer.

## Setup

Install Flutter 3.22+ with Dart 3.3+, then run:

```bash
flutter pub get
flutter analyze
flutter test
flutter run --dart-define=API_BASE_URL=http://localhost:8000
```

`API_BASE_URL` defaults to `http://localhost:8000` and is read with `String.fromEnvironment`. The mobile app only calls FastAPI; Azure credentials are never included in the bundle.

### API URL by target

- Android emulator: `http://10.0.2.2:8000`
- iOS simulator: `http://localhost:8000`
- Physical Android/iOS device: use the development machine’s LAN hostname or IP, for example `http://192.168.1.20:8000`, with the API bound to an accessible interface.

For older macOS/Xcode installations, use a Flutter SDK compatible with the installed Xcode and iOS deployment target. If CocoaPods reports a deployment-target or architecture issue, update the Podfile target only to the maximum supported by that Xcode, run `pod repo update`/`pod install`, and avoid upgrading Xcode-dependent packages blindly. Device signing, simulator builds, and native platform files were not verifiable in this environment because Flutter/Dart are not installed.

## Phase 2D scope

Text translation, Auto Detect, language loading, capabilities loading, swapping, Unicode-safe 5,000-character input, loading/error/retry states, copy, theme switching, and EN/MM switching are implemented. Voice, Camera, OCR, Documents, auth, and provider integrations are intentionally unavailable and are never simulated. A backend `503 TRANSLATION_ENGINE_NOT_CONFIGURED`, `429`, timeout, or network response is shown as an actionable error and no invented result is displayed.

History and favorites are local-only and opt-in from Settings. Nothing is saved automatically; individual successful results must be explicitly saved. Disabling the option clears the local entries.

## Verification

```bash
flutter pub get
flutter analyze
flutter test
```

Flutter/Dart checks are not runnable in environments without the Flutter SDK. Device builds remain target-environment checks and should be verified on the Android emulator, iOS simulator, and a physical device using the API URL guidance above.
