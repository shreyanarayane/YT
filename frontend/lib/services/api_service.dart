import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/models.dart';

class ApiService extends ChangeNotifier {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  static const String _configuredBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
  );
  static const String _supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const String _supabasePublishableKey = String.fromEnvironment(
    'SUPABASE_PUBLISHABLE_KEY',
  );
  String _baseUrl = _configuredBaseUrl.isNotEmpty
      ? _configuredBaseUrl
      : 'http://127.0.0.1:8000';
  String? _authToken;
  UserModel? _currentUser;
  DatabaseStatus? _dbStatus;
  bool _isLoading = false;

  String get baseUrl => _baseUrl;
  String? get authToken => _authToken;
  UserModel? get currentUser => _currentUser;
  DatabaseStatus? get dbStatus => _dbStatus;
  bool get isAuthenticated => _authToken != null && _currentUser != null;
  bool get isLoading => _isLoading;

  void setBaseUrl(String url) {
    _baseUrl = url.trim().replaceAll(RegExp(r'/+$'), '');
    notifyListeners();
  }

  void _setLoading(bool val) {
    _isLoading = val;
    notifyListeners();
  }

  Map<String, String> _headers({bool requireAuth = false}) {
    final map = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (requireAuth && _authToken != null) {
      map['Authorization'] = 'Bearer $_authToken';
    }
    return map;
  }

  Map<String, String> _supabaseHeaders() => {
    'Content-Type': 'application/json',
    'apikey': _supabasePublishableKey,
  };

  bool get _supabaseConfigured =>
      _supabaseUrl.isNotEmpty && _supabasePublishableKey.isNotEmpty;

  Future<Map<String, dynamic>> _syncSupabaseSession(String accessToken) async {
    final res = await http
        .get(
          Uri.parse('$_baseUrl/api/auth/me'),
          headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer $accessToken',
          },
        )
        .timeout(const Duration(seconds: 12));
    final data = jsonDecode(res.body);
    if (res.statusCode != 200) {
      throw Exception(
        data['detail'] ?? 'Could not validate Supabase session with the API.',
      );
    }
    _authToken = accessToken;
    _currentUser = UserModel.fromJson(Map<String, dynamic>.from(data));
    notifyListeners();
    return {'success': true, 'user': _currentUser};
  }

  // --------------------------------------------------------------------------
  // Database Endpoints
  // --------------------------------------------------------------------------
  Future<DatabaseStatus?> fetchDbStatus() async {
    try {
      final res = await http
          .get(Uri.parse('$_baseUrl/api/db/status'), headers: _headers())
          .timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        _dbStatus = DatabaseStatus.fromJson(data);
        notifyListeners();
        return _dbStatus;
      }
    } catch (e) {
      debugPrint('[ApiService] fetchDbStatus error: $e');
      // If 127.0.0.1 failed, try localhost
      if (_baseUrl.contains('127.0.0.1')) {
        try {
          final fallbackUrl = _baseUrl.replaceAll('127.0.0.1', 'localhost');
          final res = await http
              .get(Uri.parse('$fallbackUrl/api/db/status'), headers: _headers())
              .timeout(const Duration(seconds: 5));
          if (res.statusCode == 200) {
            _baseUrl = fallbackUrl;
            final data = jsonDecode(res.body);
            _dbStatus = DatabaseStatus.fromJson(data);
            notifyListeners();
            return _dbStatus;
          }
        } catch (_) {}
      }
    }
    return null;
  }

  // --------------------------------------------------------------------------
  // Auth Endpoints
  // --------------------------------------------------------------------------
  Future<Map<String, dynamic>> login(String username, String password) async {
    _setLoading(true);
    try {
      if (!_supabaseConfigured) {
        return {
          'success': false,
          'message': 'Supabase is not configured. Start Flutter with SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.',
        };
      }
      final res = await http
          .post(
            Uri.parse('$_supabaseUrl/auth/v1/token?grant_type=password'),
            headers: _supabaseHeaders(),
            body: jsonEncode({'email': username.trim(), 'password': password}),
          )
          .timeout(const Duration(seconds: 8));

      final data = jsonDecode(res.body);
      if (res.statusCode == 200 && data['access_token'] != null) {
        final synced = await _syncSupabaseSession(data['access_token']);
        await fetchDbStatus();
        return synced;
      } else {
        return {'success': false, 'message': data['detail'] ?? 'Login failed'};
      }
    } catch (e) {
      _setLoading(false);
      return {'success': false, 'message': 'Supabase sign-in failed: $e'};
    } finally {
      _setLoading(false);
    }
  }

  Future<Map<String, dynamic>> register({
    required String username,
    required String email,
    required String password,
    String? fullName,
  }) async {
    _setLoading(true);
    try {
      if (!_supabaseConfigured) {
        return {
          'success': false,
          'message': 'Supabase is not configured. Start Flutter with SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.',
        };
      }
      final res = await http
          .post(
            Uri.parse('$_supabaseUrl/auth/v1/signup'),
            headers: _supabaseHeaders(),
            body: jsonEncode({
              'email': email.trim(),
              'password': password,
              'data': {'full_name': fullName ?? username.trim()},
            }),
          )
          .timeout(const Duration(seconds: 8));

      final data = jsonDecode(res.body);
      if (res.statusCode == 200 && data['access_token'] != null) {
        final synced = await _syncSupabaseSession(data['access_token']);
        await fetchDbStatus();
        return synced;
      } else if (res.statusCode == 200) {
        return {
          'success': false,
          'message':
              'Account created. Check your email to confirm it, then sign in.',
        };
      } else {
        return {
          'success': false,
          'message': data['detail'] ?? 'Registration failed',
        };
      }
    } catch (e) {
      return {'success': false, 'message': 'Supabase sign-up failed: $e'};
    } finally {
      _setLoading(false);
    }
  }

  Future<void> logout() async {
    try {
      if (_authToken != null) {
        if (_supabaseConfigured) {
          await http
              .post(
                Uri.parse('$_supabaseUrl/auth/v1/logout'),
                headers: {
                  ..._supabaseHeaders(),
                  'Authorization': 'Bearer $_authToken',
                },
              )
              .timeout(const Duration(seconds: 3));
        }
      }
    } catch (e) {
      debugPrint('[ApiService] logout error: $e');
    }
    _authToken = null;
    _currentUser = null;
    notifyListeners();
  }

  // --------------------------------------------------------------------------
  // Topics & Research Endpoints
  // --------------------------------------------------------------------------
  Future<List<TopicItem>> fetchTopics() async {
    try {
      final res = await http
          .get(
            Uri.parse('$_baseUrl/api/topics'),
            headers: _headers(requireAuth: true),
          )
          .timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['topics'] as List<dynamic>?) ?? [];
        return list.map((e) => TopicItem.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('[ApiService] fetchTopics error: $e');
    }
    return [];
  }

  Future<TopicItem?> researchTopic(String topic) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/topics/research'),
            headers: _headers(requireAuth: true),
            body: jsonEncode({'topic': topic}),
          )
          .timeout(const Duration(seconds: 6));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return TopicItem.fromJson(data);
      }
    } catch (e) {
      debugPrint('[ApiService] researchTopic error: $e');
    }
    return null;
  }

  Future<List<String>> fetchSeedTerms() async {
    try {
      final res = await http
          .get(
            Uri.parse('$_baseUrl/api/topics/seeds'),
            headers: _headers(requireAuth: true),
          )
          .timeout(const Duration(seconds: 5));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return (data['seeds'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            [];
      }
    } catch (e) {
      debugPrint('[ApiService] fetchSeedTerms error: $e');
    }
    return [];
  }

  Future<bool> updateSeedTerms(List<String> seeds) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/topics/seeds'),
            headers: _headers(requireAuth: true),
            body: jsonEncode({'seeds': seeds}),
          )
          .timeout(const Duration(seconds: 5));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint('[ApiService] updateSeedTerms error: $e');
      return false;
    }
  }

  // --------------------------------------------------------------------------
  // Script Studio Endpoints
  // --------------------------------------------------------------------------
  Future<ScriptResult?> generateScript(
    String topic, {
    int durationSeconds = 60,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/scripts/generate'),
            headers: _headers(requireAuth: true),
            body: jsonEncode({
              'topic': topic,
              'duration_seconds': durationSeconds,
            }),
          )
          .timeout(const Duration(seconds: 12));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return ScriptResult.fromJson(data);
      }
    } catch (e) {
      debugPrint('[ApiService] generateScript error: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>> saveScriptDraft({
    required String topic,
    required String title,
    required String description,
    required String script,
    String voice = 'en-US-GuyNeural',
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/scripts/save'),
            headers: _headers(requireAuth: true),
            body: jsonEncode({
              'topic': topic,
              'title': title,
              'description': description,
              'script': script,
              'voice': voice,
            }),
          )
          .timeout(const Duration(seconds: 6));

      final data = jsonDecode(res.body);
      return Map<String, dynamic>.from(data);
    } catch (e) {
      return {'success': false, 'message': 'Failed to save draft: $e'};
    }
  }

  // --------------------------------------------------------------------------
  // Video Pipeline Endpoints
  // --------------------------------------------------------------------------
  Future<Map<String, dynamic>> buildVideo({
    required String topic,
    required String title,
    required String description,
    required String script,
    String voice = 'en-US-GuyNeural',
    bool fastMode = false,
    int? durationSeconds,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/videos/build'),
            headers: _headers(requireAuth: true),
            body: jsonEncode({
              'topic': topic,
              'title': title,
              'description': description,
              'script': script,
              'voice': voice,
              'fast_mode': fastMode,
              'duration_seconds': ?durationSeconds,
            }),
          )
          .timeout(const Duration(seconds: 40));

      final data = jsonDecode(res.body);
      return Map<String, dynamic>.from(data);
    } catch (e) {
      return {'success': false, 'message': 'Build error: $e'};
    }
  }

  Future<List<VideoProjectItem>> listVideos() async {
    try {
      final res = await http
          .get(
            Uri.parse('$_baseUrl/api/videos'),
            headers: _headers(requireAuth: true),
          )
          .timeout(const Duration(seconds: 8));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final list = (data['videos'] as List<dynamic>?) ?? [];
        return list.map((e) => VideoProjectItem.fromJson(e)).toList();
      }
    } catch (e) {
      debugPrint('[ApiService] listVideos error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>> uploadVideo(
    String localId, {
    String privacyStatus = 'private',
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/videos/$localId/upload'),
            headers: _headers(requireAuth: true),
            body: jsonEncode({'privacy_status': privacyStatus}),
          )
          .timeout(const Duration(seconds: 15));

      final data = jsonDecode(res.body);
      return Map<String, dynamic>.from(data);
    } catch (e) {
      return {'success': false, 'message': 'Upload error: $e'};
    }
  }

  Future<bool> deleteVideo(String localId) async {
    try {
      final res = await http
          .delete(
            Uri.parse('$_baseUrl/api/videos/$localId'),
            headers: _headers(requireAuth: true),
          )
          .timeout(const Duration(seconds: 6));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint('[ApiService] deleteVideo error: $e');
      return false;
    }
  }

  // --------------------------------------------------------------------------
  // Analytics & Feedback Endpoints
  // --------------------------------------------------------------------------
  Future<Map<String, dynamic>> getAnalytics() async {
    try {
      final res = await http
          .get(
            Uri.parse('$_baseUrl/api/analytics'),
            headers: _headers(requireAuth: true),
          )
          .timeout(const Duration(seconds: 6));

      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint('[ApiService] getAnalytics error: $e');
    }
    return {'topics': [], 'total_learned_topics': 0, 'summary': {}};
  }

  Future<Map<String, dynamic>> submitFeedback({
    required String topic,
    required double score,
    int attempts = 1,
    int views = 250,
    int subscribersGained = 5,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/analytics/feedback'),
            headers: _headers(requireAuth: true),
            body: jsonEncode({
              'topic': topic,
              'score': score,
              'attempts': attempts,
              'views': views,
              'subscribers_gained': subscribersGained,
            }),
          )
          .timeout(const Duration(seconds: 6));

      final data = jsonDecode(res.body);
      return Map<String, dynamic>.from(data);
    } catch (e) {
      return {'success': false, 'message': 'Feedback error: $e'};
    }
  }

  // --------------------------------------------------------------------------
  // Configuration Endpoints
  // --------------------------------------------------------------------------
  Future<ChannelConfig?> getConfig() async {
    try {
      final res = await http
          .get(
            Uri.parse('$_baseUrl/api/config'),
            headers: _headers(requireAuth: true),
          )
          .timeout(const Duration(seconds: 5));

      if (res.statusCode == 200) {
        return ChannelConfig.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint('[ApiService] getConfig error: $e');
    }
    return null;
  }

  Future<bool> updateConfig(Map<String, dynamic> configMap) async {
    try {
      final res = await http
          .post(
            Uri.parse('$_baseUrl/api/config'),
            headers: _headers(requireAuth: true),
            body: jsonEncode(configMap),
          )
          .timeout(const Duration(seconds: 6));
      return res.statusCode == 200;
    } catch (e) {
      debugPrint('[ApiService] updateConfig error: $e');
      return false;
    }
  }
}
