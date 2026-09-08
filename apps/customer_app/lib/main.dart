import 'package:flutter/material.dart';
import 'package:hb_shared/hb_shared.dart';
import 'package:provider/provider.dart';

import 'app_config.dart';
import 'screens/home/main_shell.dart';
import 'screens/login/email_screen.dart';
import 'screens/splash_screen.dart';
import 'state/auth_state.dart';
import 'state/cart_state.dart';

void main() {
  final authStorage = AuthStorage();
  final api = ApiClient(baseUrl: AppConfig.apiBaseUrl, authStorage: authStorage);

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider(create: (_) => AuthState(api)..bootstrap()),
        ChangeNotifierProvider(create: (_) => CartState()),
      ],
      child: const HungerBirdsApp(),
    ),
  );
}

class HungerBirdsApp extends StatelessWidget {
  const HungerBirdsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hunger Birds',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: const AuthGate(),
    );
  }
}

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    final status = context.watch<AuthState>().status;
    return switch (status) {
      AuthStatus.unknown => const SplashScreen(),
      AuthStatus.loggedOut => const EmailScreen(),
      AuthStatus.loggedIn => const MainShell(),
    };
  }
}
