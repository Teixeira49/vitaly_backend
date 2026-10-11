---
name: "managing-secure-storage"
description: "Deep guide for flutter_secure_storage (v10.x) in estei-mobile: encrypted key-value storage of sensitive data (auth/OTP/security tokens, credentials, PII) via iOS Keychain / Android Keystore. This is the canonical secure-storage skill: platform config (Android backup exclusion, biometric invalidation, iOS Keychain accessibility) plus the project's data_source pattern (DeviceSecureStorageApi implements DeviceStorage, injected via AppConfig, consumed through repositories). Uses flutter_bloc + constructor injection, NOT static global wrappers and NOT Riverpod."
metadata:
  last_modified: "2026-07-10"
---

# SecureStorage Deep Guide (flutter_secure_storage v10.x) — estei-mobile

## Goal
Store sensitive data (auth token `authorization`, `x-otp-token`, `x-security-token`,
credentials, PII) in platform-encrypted stores (iOS Keychain, Android Keystore). This is the
**canonical, in-depth secure-storage skill** for the repo: it owns the platform configuration
AND the project's data_source pattern. For the high-level 2-engine decision (SecureStorage vs
SharedPreferences), see the `flutter-db` skill, which points here for the deep details.

> **Project pattern (non-negotiable):** secure storage is a **data_source implementing the
> `DeviceStorage` interface**, injected via `AppConfig` in `lib/main_*.dart`, and consumed
> through repositories that return `Result<T, AppError>`. Do NOT use a static global wrapper,
> Riverpod, or direct `http` calls. This project uses `flutter_bloc` + constructor injection.

## Process

### Phase 1: Install
`flutter_secure_storage` is already in `pubspec.yaml` (`^10.0.0-beta.4`).

### Phase 2: Platform Configuration

**Android (android/app/build.gradle):** min SDK 18+.
```gradle
android {
    compileSdkVersion 34
    defaultConfig { minSdkVersion 18 }
}
```

**Android backup exclusion (AndroidManifest.xml)** — prevents encrypted tokens from leaking
into Google Drive backups (they can't be restored on a new device and cause crashes):
```xml
<application
  android:fullBackupContent="@xml/backup_rules"
  android:allowBackup="true">
```

**Android backup rules (res/xml/backup_rules.xml):**
```xml
<?xml version="1.0" encoding="utf-8"?>
<full-backup-content>
  <exclude domain="sharedpref" path="FlutterSecureStorage"/>
</full-backup-content>
```

**iOS:** uses Keychain by default. Add the "Keychain Sharing" capability in Xcode if you hit
entitlement errors.

### Phase 3: The data_source (the project pattern)

Wrap the plugin in a class implementing the `DeviceStorage` interface. This is the real
implementation at `lib/src/data/data_sources/device_storage_api/device_secure_storage_api.dart`,
extended here with the recommended platform options:

```dart
import 'package:avilatek_core/http.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class DeviceSecureStorageApi implements DeviceStorage {
  const DeviceSecureStorageApi();

  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
      resetOnError: true, // auto-reset when Keystore keys are invalidated
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
  );

  @override
  Future<void> setValue({required String key, required String value}) =>
      _storage.write(key: key, value: value);

  @override
  Future<String?> getValue(String key) => _storage.read(key: key);

  @override
  Future<void> deleteValue(String key) => _storage.delete(key: key);
}
```

### Phase 4: Injection & consumption

Inject via `AppConfig` per flavor (never a static global):
```dart
const deviceStorage = DeviceSecureStorageApi();
// ...passed into AppConfig / the repositories that require a DeviceStorage
```

Repositories own the keys and expose typed results — UI/blocs never touch storage directly.
Real keys in this repo: `HttpHeaders.authorizationHeader`, `HttpHeadersExtensions.otpTokenHeader`,
`HttpHeadersExtensions.securityTokenHeader`:

```dart
class AuthRepository {
  AuthRepository({required DeviceStorage deviceStorage})
      : _deviceStorage = deviceStorage;
  final DeviceStorage _deviceStorage;

  Future<void> _persistAuthToken(String token) =>
      _deviceStorage.setValue(key: HttpHeaders.authorizationHeader, value: token);

  Future<String?> _authToken() =>
      _deviceStorage.getValue(HttpHeaders.authorizationHeader);
}
```

Blocs consume the repository and drive state with `SendAsyncState`/`Result.resolve` (see the
`implementing-flutter-bloc` skill). Auth requests route through `HttpManager`/`simple_graphql`
with header injection — NOT hand-rolled `http.get` with a manual `Bearer` header.

## Production Issues & Best Practices

### Biometric change invalidation
**Problem:** the user adds/removes a fingerprint → Android Keystore keys become invalid and
reads throw `KeyPermanentlyInvalidatedException`.
**Solution:** `resetOnError: true` in `AndroidOptions` (already set in Phase 3). Surface a
re-authentication flow to the user via the repository/bloc — do NOT show dialogs from storage:

```dart
// In the repository, map the failure to an AppError; the bloc reacts and the UI
// (via BlocListener) navigates to login. Keep storage free of BuildContext.
try {
  final token = await _deviceStorage.getValue(HttpHeaders.authorizationHeader);
} on Exception {
  // return a Result.failure(AppError.sessionInvalidated) — bloc handles re-login
}
```

### Data migration
If a value ever moves from SharedPreferences to SecureStorage, read-old → write-new →
remove-old once, guarded by a migration flag. Keep the migration in the data/repository layer,
not in `main()`.

### iOS Keychain accessibility
`KeychainAccessibility.first_unlock` is the recommended balance (readable after first unlock,
survives backgrounding). More restrictive options: `unlocked`, `first_unlock_this_device`
(never migrates to a new device), `unlocked_this_device`.

### Google Drive backup
Keystore keys don't restore from backups; excluding FlutterSecureStorage (Phase 2) prevents
crashes on restored devices. Verify with `adb shell bmgr backupnow --all`.

## Constraints
* **Sensitive data ONLY**: tokens/credentials/PII here; UX prefs → SharedPreferences (see `flutter-db`).
* **Data_source + injection**: implement `DeviceStorage`, inject via `AppConfig`. NO static global wrapper, NO Riverpod.
* **Repository boundary**: UI/blocs never touch storage; go through a repository returning `Result<T, AppError>`.
* **No BuildContext in storage**: handle biometric/invalidation via repository→bloc→UI, not dialogs from the storage layer.
* **Async only / strings only**: all ops are `Future`s; serialize complex objects to JSON.
* **Backup exclusion**: always exclude FlutterSecureStorage from cloud backups.
* **Logout cleanup**: clear tokens on logout (the repo already deletes authorization/otp/security keys).
* **Logging**: use `dart:developer` `log(...)`, never `print`.
