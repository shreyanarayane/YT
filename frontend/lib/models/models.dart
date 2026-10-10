class UserModel {
  final String id;
  final String username;
  final String email;
  final String fullName;
  final bool isAdmin;
  final String? createdAt;

  UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.fullName,
    required this.isAdmin,
    this.createdAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id']?.toString() ?? '',
      username: json['username'] ?? json['email'] ?? '',
      email: json['email'] ?? '',
      fullName: json['full_name'] ?? json['username'] ?? '',
      isAdmin: json['is_admin'] ?? false,
      createdAt: json['created_at'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'email': email,
        'full_name': fullName,
        'is_admin': isAdmin,
        'created_at': createdAt,
      };
}

class DatabaseStatus {
  final bool connected;
  final String dialect;
  final String url;
  final Map<String, dynamic> stats;
  final String message;

  DatabaseStatus({
    required this.connected,
    required this.dialect,
    required this.url,
    required this.stats,
    required this.message,
  });

  factory DatabaseStatus.fromJson(Map<String, dynamic> json) {
    return DatabaseStatus(
      connected: json['connected'] ?? false,
      dialect: json['dialect'] ?? 'unknown',
      url: json['url'] ?? '',
      stats: json['stats'] is Map ? Map<String, dynamic>.from(json['stats']) : {},
      message: json['message'] ?? '',
    );
  }
}

class TopicItem {
  final String topic;
  final double score;
  final bool needsReview;
  final bool allowed;
  final String? reason;

  TopicItem({
    required this.topic,
    required this.score,
    this.needsReview = false,
    this.allowed = true,
    this.reason,
  });

  factory TopicItem.fromJson(Map<String, dynamic> json) {
    return TopicItem(
      topic: json['topic'] ?? '',
      score: (json['score'] is num) ? (json['score'] as num).toDouble() : 0.5,
      needsReview: json['needs_review'] ?? false,
      allowed: json['allowed'] ?? true,
      reason: json['reason'],
    );
  }
}

class ScriptResult {
  final String topic;
  final String title;
  final String description;
  final String script;
  final bool needsReview;

  ScriptResult({
    required this.topic,
    required this.title,
    required this.description,
    required this.script,
    this.needsReview = false,
  });

  factory ScriptResult.fromJson(Map<String, dynamic> json) {
    return ScriptResult(
      topic: json['topic'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      script: json['script'] ?? '',
      needsReview: json['needs_review'] ?? false,
    );
  }
}

class VideoProjectItem {
  final int? id;
  final String localId;
  final String topic;
  final String title;
  final String description;
  final String script;
  final String voice;
  final String status;
  final String? youtubeVideoId;
  final String privacyStatus;
  final bool hasVideo;
  final bool hasAudio;
  final String? videoUrl;
  final String? narrationUrl;
  final String? createdAt;

  VideoProjectItem({
    this.id,
    required this.localId,
    required this.topic,
    required this.title,
    required this.description,
    required this.script,
    required this.voice,
    required this.status,
    this.youtubeVideoId,
    required this.privacyStatus,
    required this.hasVideo,
    required this.hasAudio,
    this.videoUrl,
    this.narrationUrl,
    this.createdAt,
  });

  factory VideoProjectItem.fromJson(Map<String, dynamic> json) {
    return VideoProjectItem(
      id: json['id'],
      localId: json['local_id'] ?? '',
      topic: json['topic'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      script: json['script'] ?? '',
      voice: json['voice'] ?? 'en-US-GuyNeural',
      status: json['status'] ?? 'draft',
      youtubeVideoId: json['youtube_video_id'],
      privacyStatus: json['privacy_status'] ?? 'private',
      hasVideo: json['has_video'] ?? false,
      hasAudio: json['has_audio'] ?? false,
      videoUrl: json['video_url'],
      narrationUrl: json['narration_url'],
      createdAt: json['created_at'],
    );
  }
}

class AnalyticsItem {
  final String topic;
  final double score;
  final int attempts;
  final Map<String, dynamic> lastStats;

  AnalyticsItem({
    required this.topic,
    required this.score,
    required this.attempts,
    required this.lastStats,
  });

  factory AnalyticsItem.fromJson(Map<String, dynamic> json) {
    return AnalyticsItem(
      topic: json['topic'] ?? '',
      score: (json['score'] is num) ? (json['score'] as num).toDouble() : 0.5,
      attempts: json['attempts'] ?? 0,
      lastStats: json['last_stats'] is Map ? Map<String, dynamic>.from(json['last_stats']) : {},
    );
  }
}

class ChannelConfig {
  final String channelName;
  final List<String> seedTerms;
  final int targetSeconds;
  final String voice;
  final String defaultPrivacy;
  final Map<String, dynamic> integrations;

  ChannelConfig({
    required this.channelName,
    required this.seedTerms,
    required this.targetSeconds,
    required this.voice,
    required this.defaultPrivacy,
    required this.integrations,
  });

  factory ChannelConfig.fromJson(Map<String, dynamic> json) {
    return ChannelConfig(
      channelName: json['channel_name'] ?? 'advpipe',
      seedTerms: (json['seed_terms'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      targetSeconds: json['target_seconds'] ?? 50,
      voice: json['voice'] ?? 'en-US-GuyNeural',
      defaultPrivacy: json['default_privacy'] ?? 'private',
      integrations: json['integrations'] is Map ? Map<String, dynamic>.from(json['integrations']) : {},
    );
  }
}
