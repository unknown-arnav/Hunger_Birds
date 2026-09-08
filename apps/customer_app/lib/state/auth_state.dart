import 'package:flutter/foundation.dart';
import 'package:hb_shared/hb_shared.dart';

enum AuthStatus { unknown, loggedOut, loggedIn }

class AuthState extends ChangeNotifier {
  final ApiClient api;

  AuthState(this.api);

  AuthStatus status = AuthStatus.unknown;
  AppUser? currentUser;

  Future<void> bootstrap() async {
    await api.authStorage.load();
    if (!api.authStorage.isLoggedIn) {
      status = AuthStatus.loggedOut;
      notifyListeners();
      return;
    }
    try {
      currentUser = await api.me();
      status = AuthStatus.loggedIn;
    } catch (_) {
      await api.authStorage.clear();
      status = AuthStatus.loggedOut;
    }
    notifyListeners();
  }

  Future<OtpRequestResult> requestOtp(String email) => api.requestOtp(email);

  Future<void> verifyOtp(String email, String code) async {
    final result = await api.verifyOtp(email, code);
    currentUser = result.user;
    status = AuthStatus.loggedIn;
    notifyListeners();
  }

  Future<void> refreshCurrentUser() async {
    currentUser = await api.me();
    notifyListeners();
  }

  Future<void> logout() async {
    await api.logout();
    currentUser = null;
    status = AuthStatus.loggedOut;
    notifyListeners();
  }
}
