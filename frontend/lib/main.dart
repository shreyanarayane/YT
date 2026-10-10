import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'services/api_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const YouTubeAgentApp());
}

class YouTubeAgentApp extends StatefulWidget {
  const YouTubeAgentApp({super.key});

  @override
  State<YouTubeAgentApp> createState() => _YouTubeAgentAppState();
}

class _YouTubeAgentAppState extends State<YouTubeAgentApp> {
  final _api = ApiService();

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _api,
      builder: (context, _) {
        return MaterialApp(
          title: 'AI YouTube Content Manager',
          debugShowCheckedModeBanner: false,
          themeMode: ThemeMode.dark,
          theme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.light,
            colorSchemeSeed: const Color(0xFF6366F1),
            scaffoldBackgroundColor: const Color(0xFFF8FAFC),
            cardTheme: CardThemeData(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              color: Colors.white,
            ),
            appBarTheme: const AppBarTheme(
              elevation: 0,
              backgroundColor: Colors.white,
              foregroundColor: Color(0xFF0F172A),
            ),
          ),
          darkTheme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.dark,
            colorSchemeSeed: const Color(0xFF818CF8),
            scaffoldBackgroundColor: const Color(0xFF0F172A),
            cardTheme: CardThemeData(
              elevation: 3,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              color: const Color(0xFF1E293B),
            ),
            appBarTheme: const AppBarTheme(
              elevation: 0,
              backgroundColor: Color(0xFF1E293B),
              foregroundColor: Colors.white,
            ),
          ),
          home: _api.isAuthenticated ? const DashboardScreen() : const LoginScreen(),
        );
      },
    );
  }
}
