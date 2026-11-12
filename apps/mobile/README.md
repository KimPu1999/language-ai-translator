# Lingua Mobile — Phase 3E

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

## Phase 3 scope

Text translation, voice recording, real speech-to-text, editable Myanmar Unicode transcripts, Phase 2 text translation, Azure-backed TTS playback, language/voice selectors, loading/error/retry states, theme switching, and EN/MM switching are implemented. Camera, OCR, Documents, auth, and provider keys remain outside the app. Recording begins only after explicit user action and stops on cancel, lifecycle changes, unmount, or 15 seconds. Temporary recording and playback files are deleted and are never added to local history.

The existing Phase 3B FastAPI contract accepts bounded raw audio bytes with an `audio/*` content type and `locale` query parameter. The mobile client sends the selected recording bytes directly to that contract; it does not fabricate multipart fields that the current backend does not accept.

### Native microphone setup

When generating platform folders, add `android.permission.RECORD_AUDIO` to the Android application manifest and `NSMicrophoneUsageDescription` to iOS `Info.plist`. The `record` package still requests permission at runtime; the app never starts a recorder before `hasPermission()` succeeds. `AudioEncoder.opus` is preferred and AAC/M4A is selected when Opus is unavailable.

History and favorites are local-only and opt-in from Settings. Nothing is saved automatically; individual successful results must be explicitly saved. Disabling the option clears the local entries.

## Two-way conversation

The Conversation route provides independent Person A and Person B speech/target language and voice profiles. Turns use push-to-talk, one recorder at a time, a 15-second limit, editable transcripts, the existing FastAPI transcription/translation/TTS calls, and per-turn replay. Unique turn IDs and a controller version invalidate stale responses. Audio remains in temporary files only and is removed after use or session clear; text is saved only through the explicit local-save action when Settings enables local saving. This is turn-based and does not claim full-duplex streaming or cloud synchronization.

## Verification

```bash
flutter pub get
flutter analyze
flutter test
```

Flutter/Dart checks are not runnable in environments without the Flutter SDK. Device builds remain target-environment checks and should be verified on the Android emulator, iOS simulator, and a physical device using the API URL guidance above.
