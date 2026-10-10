import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/models.dart';
import '../services/api_service.dart';
import 'login_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen>
    with SingleTickerProviderStateMixin {
  final _api = ApiService();
  late TabController _tabController;

  // Topics State
  List<TopicItem> _topics = [];
  List<String> _seedTerms = [];
  bool _isLoadingTopics = false;
  final _customTopicController = TextEditingController();
  TopicItem? _researchedTopic;

  // Script Studio State
  final _scriptTopicController = TextEditingController();
  final _scriptTitleController = TextEditingController();
  final _scriptDescController = TextEditingController();
  final _scriptBodyController = TextEditingController();
  String _selectedVoice = 'en-US-GuyNeural';
  bool _isGeneratingScript = false;
  bool _isBuildingVideo = false;
  bool _autoPublish = false;
  String _autoPublishPrivacy = 'private';

  // Video Studio State
  List<VideoProjectItem> _videos = [];
  bool _isLoadingVideos = false;
  String _videoFilter = 'all';

  // Analytics State
  Map<String, dynamic> _analyticsData = {};

  // Settings State
  final _channelNameController = TextEditingController();
  final _targetSecondsController = TextEditingController();
  final _pexelsKeyController = TextEditingController();
  String _defaultPrivacy = 'private';

  final List<String> _availableVoices = [
    'en-US-GuyNeural',
    'en-US-JennyNeural',
    'en-US-ChristopherNeural',
    'en-GB-SoniaNeural',
    'en-GB-RyanNeural',
    'en-IN-PrabhatNeural',
    'en-IN-NeerjaNeural',
    'en-AU-WilliamNeural',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 5, vsync: this);
    _loadInitialData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _customTopicController.dispose();
    _scriptTopicController.dispose();
    _scriptTitleController.dispose();
    _scriptDescController.dispose();
    _scriptBodyController.dispose();
    _channelNameController.dispose();
    _targetSecondsController.dispose();
    _pexelsKeyController.dispose();
    super.dispose();
  }

  void _loadInitialData() {
    _fetchTopics();
    _fetchSeedTerms();
    _fetchVideos();
    _fetchAnalytics();
    _fetchConfig();
  }

  void _showMessage(String msg, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: isError ? Colors.redAccent : const Color(0xFF10B981),
        duration: const Duration(seconds: 3),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  // --------------------------------------------------------------------------
  // Data Fetchers
  // --------------------------------------------------------------------------
  Future<void> _fetchTopics() async {
    setState(() => _isLoadingTopics = true);
    final list = await _api.fetchTopics();
    if (mounted) {
      setState(() {
        _topics = list;
        _isLoadingTopics = false;
      });
    }
  }

  Future<void> _fetchSeedTerms() async {
    final list = await _api.fetchSeedTerms();
    if (mounted) {
      setState(() => _seedTerms = list);
    }
  }

  Future<void> _fetchVideos() async {
    setState(() => _isLoadingVideos = true);
    final list = await _api.listVideos();
    if (mounted) {
      setState(() {
        _videos = list;
        _isLoadingVideos = false;
      });
    }
  }

  Future<void> _fetchAnalytics() async {
    final data = await _api.getAnalytics();
    if (mounted) {
      setState(() {
        _analyticsData = data;
      });
    }
  }

  Future<void> _fetchConfig() async {
    final cfg = await _api.getConfig();
    if (mounted && cfg != null) {
      setState(() {
        _channelNameController.text = cfg.channelName;
        _targetSecondsController.text = cfg.targetSeconds.toString();
        _selectedVoice = cfg.voice;
        _defaultPrivacy = cfg.defaultPrivacy;
      });
    }
  }

  // --------------------------------------------------------------------------
  // Topic Discovery Actions
  // --------------------------------------------------------------------------
  Future<void> _researchCustomTopic() async {
    final t = _customTopicController.text.trim();
    if (t.isEmpty) {
      _showMessage('Enter a topic to research', isError: true);
      return;
    }
    final item = await _api.researchTopic(t);
    if (mounted && item != null) {
      setState(() => _researchedTopic = item);
      if (item.allowed) {
        _showMessage(
          '✓ Topic passed content filter (Score: ${item.score.toStringAsFixed(2)})',
        );
      } else {
        _showMessage(
          '⚠ Topic flagged: ${item.reason ?? "Safety filter"}',
          isError: true,
        );
      }
    }
  }

  void _sendTopicToStudio(String topic) {
    setState(() {
      _scriptTopicController.text = topic;
      _tabController.animateTo(1);
    });
    _generateScriptForTopic(topic);
  }

  void _showAddSeedDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Niche Seed Term'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'e.g. crypto investing, ai tools',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final term = controller.text.trim();
              if (term.isNotEmpty) {
                final updated = List<String>.from(_seedTerms)..add(term);
                final success = await _api.updateSeedTerms(updated);
                if (success) {
                  setState(() => _seedTerms = updated);
                  _showMessage('Added seed term: $term');
                  _fetchTopics();
                }
              }
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Add Seed'),
          ),
        ],
      ),
    );
  }

  Future<void> _removeSeedTerm(String term) async {
    final updated = List<String>.from(_seedTerms)..remove(term);
    final success = await _api.updateSeedTerms(updated);
    if (success) {
      setState(() => _seedTerms = updated);
      _showMessage('Removed seed term: $term');
      _fetchTopics();
    }
  }

  // --------------------------------------------------------------------------
  // Script Studio Actions
  // --------------------------------------------------------------------------
  Future<void> _generateScriptForTopic([String? customTopic]) async {
    final topic = customTopic ?? _scriptTopicController.text.trim();
    if (topic.isEmpty) {
      _showMessage('Please enter or select a topic first', isError: true);
      return;
    }

    setState(() => _isGeneratingScript = true);
    final targetSeconds =
        int.tryParse(_targetSecondsController.text.trim()) ?? 60;
    final result = await _api.generateScript(
      topic,
      durationSeconds: targetSeconds,
    );
    if (mounted) {
      setState(() => _isGeneratingScript = false);
      if (result != null) {
        _scriptTopicController.text = result.topic;
        _scriptTitleController.text = result.title;
        _scriptDescController.text = result.description;
        _scriptBodyController.text = result.script;
        _showMessage('✓ Script generated for "${result.topic}"');
      } else {
        _showMessage('Failed to generate script', isError: true);
      }
    }
  }

  Future<void> _saveDraft() async {
    if (_scriptBodyController.text.trim().isEmpty) {
      _showMessage('Cannot save an empty script', isError: true);
      return;
    }
    final res = await _api.saveScriptDraft(
      topic: _scriptTopicController.text.trim(),
      title: _scriptTitleController.text.trim(),
      description: _scriptDescController.text.trim(),
      script: _scriptBodyController.text.trim(),
      voice: _selectedVoice,
    );
    if (res['success'] == true) {
      _showMessage('✓ Script draft saved (ID: ${res['local_id']})');
      _fetchVideos();
    } else {
      _showMessage(res['message'] ?? 'Save failed', isError: true);
    }
  }

  Future<void> _buildVideoPipeline() async {
    final script = _scriptBodyController.text.trim();
    if (script.isEmpty) {
      _showMessage('Please generate or write a script first', isError: true);
      return;
    }

    setState(() => _isBuildingVideo = true);
    _showMessage('🚀 Synthesizing voice & building video pipeline...');

    final res = await _api.buildVideo(
      topic: _scriptTopicController.text.trim(),
      title: _scriptTitleController.text.trim().isNotEmpty
          ? _scriptTitleController.text.trim()
          : 'AI Shorts: ${_scriptTopicController.text.trim()}',
      description: _scriptDescController.text.trim(),
      script: script,
      voice: _selectedVoice,
      durationSeconds: int.tryParse(_targetSecondsController.text.trim()),
    );

    if (mounted) {
      setState(() => _isBuildingVideo = false);
      if (res['success'] == true) {
        final localId = res['local_id'];
        _showMessage('✓ Video Build Completed! ID: $localId');
        _fetchVideos();

        if (_autoPublish) {
          _showMessage('Uploading video to YouTube ($_autoPublishPrivacy)...');
          final uploadRes = await _api.uploadVideo(
            localId,
            privacyStatus: _autoPublishPrivacy,
          );
          if (uploadRes['success'] == true) {
            _showMessage(
              '✓ Published to YouTube! ID: ${uploadRes['youtube_video_id']}',
            );
            _fetchVideos();
          } else {
            _showMessage(
              'Upload warning: ${uploadRes['message']}',
              isError: true,
            );
          }
        }

        _tabController.animateTo(2);
      } else {
        _showMessage(res['message'] ?? 'Video build failed', isError: true);
      }
    }
  }

  // --------------------------------------------------------------------------
  // Video Studio Actions
  // --------------------------------------------------------------------------
  void _showUploadDialog(VideoProjectItem video) {
    String privacy = 'private';
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Publish Video: ${video.title}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Local ID: ${video.localId}'),
              const SizedBox(height: 12),
              const Text('Select YouTube Privacy Status:'),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: privacy,
                decoration: const InputDecoration(border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(
                    value: 'private',
                    child: Text('Private (Recommended for review)'),
                  ),
                  DropdownMenuItem(value: 'unlisted', child: Text('Unlisted')),
                  DropdownMenuItem(
                    value: 'public',
                    child: Text('Public (Instant live)'),
                  ),
                ],
                onChanged: (val) =>
                    setDialogState(() => privacy = val ?? 'private'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                Navigator.pop(ctx);
                _showMessage('Publishing video to YouTube...');
                final res = await _api.uploadVideo(
                  video.localId,
                  privacyStatus: privacy,
                );
                if (res['success'] == true) {
                  _showMessage('✓ ${res['message']}');
                  _fetchVideos();
                } else {
                  _showMessage(
                    res['message'] ?? 'Upload failed',
                    isError: true,
                  );
                }
              },
              icon: const Icon(Icons.cloud_upload_rounded),
              label: const Text('Confirm Upload'),
            ),
          ],
        ),
      ),
    );
  }

  void _showVideoDetails(VideoProjectItem video) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(video.title),
        content: SizedBox(
          width: 500,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Chip(
                  label: Text('Status: ${video.status.toUpperCase()}'),
                  backgroundColor:
                      video.status == 'ready' || video.status == 'uploaded'
                      ? const Color(0xFF10B981).withValues(alpha: 0.2)
                      : Colors.orange.withValues(alpha: 0.2),
                ),
                const SizedBox(height: 8),
                Text(
                  'Topic: ${video.topic}',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text('Voice: ${video.voice}'),
                if (video.youtubeVideoId != null)
                  Text(
                    'YouTube ID: ${video.youtubeVideoId}',
                    style: const TextStyle(color: Colors.redAccent),
                  ),
                const Divider(height: 24),
                const Text(
                  'Description:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Text(video.description.isEmpty ? 'None' : video.description),
                const SizedBox(height: 12),
                const Text(
                  'Script:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest
                        .withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(video.script),
                ),
                if (video.videoUrl != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Video URL: ${_api.baseUrl}${video.videoUrl}',
                    style: const TextStyle(fontSize: 12, color: Colors.blue),
                  ),
                ],
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          ElevatedButton.icon(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: video.script));
              _showMessage('Script copied to clipboard');
              Navigator.pop(ctx);
            },
            icon: const Icon(Icons.copy, size: 16),
            label: const Text('Copy Script'),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteVideo(String localId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Video Project?'),
        content: Text('Are you sure you want to delete build $localId?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.redAccent,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      final success = await _api.deleteVideo(localId);
      if (success) {
        _showMessage('Project $localId deleted');
        _fetchVideos();
      } else {
        _showMessage('Failed to delete project', isError: true);
      }
    }
  }

  // --------------------------------------------------------------------------
  // Analytics Feedback Action
  // --------------------------------------------------------------------------
  void _showFeedbackDialog([String? initialTopic]) {
    final topicCtrl = TextEditingController(
      text: initialTopic ?? (_topics.isNotEmpty ? _topics.first.topic : ''),
    );
    double score = 0.85;
    final viewsCtrl = TextEditingController(text: '1200');
    final subsCtrl = TextEditingController(text: '18');

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Submit Analytics & Train Model'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: topicCtrl,
                decoration: const InputDecoration(
                  labelText: 'Topic Name',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Performance Rating: ${(score * 100).toInt()}% (${score.toStringAsFixed(2)})',
              ),
              Slider(
                value: score,
                min: 0.1,
                max: 1.0,
                divisions: 18,
                label: score.toStringAsFixed(2),
                onChanged: (val) => setDialogState(() => score = val),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: viewsCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Views',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: subsCtrl,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Subs Gained',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final topic = topicCtrl.text.trim();
                if (topic.isNotEmpty) {
                  final res = await _api.submitFeedback(
                    topic: topic,
                    score: score,
                    views: int.tryParse(viewsCtrl.text) ?? 500,
                    subscribersGained: int.tryParse(subsCtrl.text) ?? 5,
                  );
                  if (res['success'] == true) {
                    _showMessage(
                      '✓ Feedback recorded! New Topic Weight: ${res['new_score']}',
                    );
                    _fetchAnalytics();
                    _fetchTopics();
                  }
                }
                if (ctx.mounted) Navigator.pop(ctx);
              },
              child: const Text('Save Feedback'),
            ),
          ],
        ),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // Settings Actions
  // --------------------------------------------------------------------------
  Future<void> _saveSettings() async {
    final success = await _api.updateConfig({
      'channel_name': _channelNameController.text.trim(),
      'target_seconds':
          int.tryParse(_targetSecondsController.text.trim()) ?? 50,
      'voice': _selectedVoice,
      'default_privacy': _defaultPrivacy,
      if (_pexelsKeyController.text.trim().isNotEmpty)
        'pexels_api_key': _pexelsKeyController.text.trim(),
    });
    if (success) {
      _showMessage('✓ Settings saved successfully');
      _fetchConfig();
    } else {
      _showMessage('Failed to save settings', isError: true);
    }
  }

  void _handleLogout() {
    _api.logout();
    Navigator.of(
      context,
    ).pushReplacement(MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  // --------------------------------------------------------------------------
  // UI Builder
  // --------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    final dbStatus = _api.dbStatus;
    final user = _api.currentUser;

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.smart_display_rounded, color: Colors.redAccent),
            const SizedBox(width: 8),
            const Text(
              'AI YouTube Studio',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
            ),
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: (dbStatus?.connected ?? false)
                    ? const Color(0xFF10B981).withValues(alpha: 0.15)
                    : Colors.redAccent.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: (dbStatus?.connected ?? false)
                          ? const Color(0xFF10B981)
                          : Colors.redAccent,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'DB: ${dbStatus?.dialect ?? "Supabase"}',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: (dbStatus?.connected ?? false)
                          ? const Color(0xFF10B981)
                          : Colors.redAccent,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          if (user != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Chip(
                avatar: const CircleAvatar(
                  backgroundColor: Colors.indigo,
                  child: Icon(Icons.person, size: 14, color: Colors.white),
                ),
                label: Text(user.username),
              ),
            ),
          IconButton(
            tooltip: 'Logout',
            icon: const Icon(Icons.logout_rounded),
            onPressed: _handleLogout,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: const [
            Tab(icon: Icon(Icons.trending_up_rounded), text: 'Topics & Trends'),
            Tab(icon: Icon(Icons.edit_note_rounded), text: 'Script Studio'),
            Tab(icon: Icon(Icons.video_library_rounded), text: 'Video Studio'),
            Tab(icon: Icon(Icons.insights_rounded), text: 'AI Learning'),
            Tab(icon: Icon(Icons.settings_rounded), text: 'Settings'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildTopicsTab(),
          _buildScriptStudioTab(),
          _buildVideoStudioTab(),
          _buildAnalyticsTab(),
          _buildSettingsTab(),
        ],
      ),
    );
  }

  // --------------------------------------------------------------------------
  // TAB 1: Topics & Trends
  // --------------------------------------------------------------------------
  Widget _buildTopicsTab() {
    return RefreshIndicator(
      onRefresh: () async {
        await _fetchTopics();
        await _fetchSeedTerms();
      },
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _buildKpiCard(
                  'Ranked Topics',
                  '${_topics.length}',
                  Icons.auto_awesome,
                  Colors.purple,
                ),
                const SizedBox(width: 12),
                _buildKpiCard(
                  'Seed Niches',
                  '${_seedTerms.length}',
                  Icons.tag,
                  Colors.blue,
                ),
                const SizedBox(width: 12),
                _buildKpiCard(
                  'Built Videos',
                  '${_videos.length}',
                  Icons.movie_creation_outlined,
                  Colors.teal,
                ),
              ],
            ),
            const SizedBox(height: 16),

            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Target Niche Seeds (Trends Query Engines):',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _showAddSeedDialog,
                          icon: const Icon(Icons.add, size: 16),
                          label: const Text('Add Seed'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: _seedTerms
                          .map(
                            (s) => Chip(
                              label: Text(s),
                              onDeleted: () => _removeSeedTerm(s),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _customTopicController,
                        decoration: const InputDecoration(
                          hintText:
                              'Enter custom topic to test safety & score...',
                          prefixIcon: Icon(Icons.search),
                          border: OutlineInputBorder(),
                          isDense: true,
                        ),
                        onSubmitted: (_) => _researchCustomTopic(),
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      onPressed: _researchCustomTopic,
                      icon: const Icon(Icons.analytics_outlined),
                      label: const Text('Analyze Topic'),
                    ),
                  ],
                ),
              ),
            ),

            if (_researchedTopic != null) ...[
              const SizedBox(height: 8),
              Card(
                color: _researchedTopic!.allowed
                    ? const Color(0xFF10B981).withValues(alpha: 0.1)
                    : Colors.redAccent.withValues(alpha: 0.1),
                child: ListTile(
                  leading: Icon(
                    _researchedTopic!.allowed
                        ? Icons.check_circle
                        : Icons.warning,
                    color: _researchedTopic!.allowed
                        ? const Color(0xFF10B981)
                        : Colors.redAccent,
                  ),
                  title: Text(
                    _researchedTopic!.topic,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    'Status: ${_researchedTopic!.allowed ? "Allowed" : "Blocked"} | Score: ${_researchedTopic!.score.toStringAsFixed(2)} | Reason: ${_researchedTopic!.reason ?? "Passed"}',
                  ),
                  trailing: ElevatedButton(
                    onPressed: () =>
                        _sendTopicToStudio(_researchedTopic!.topic),
                    child: const Text('Create Script'),
                  ),
                ),
              ),
            ],

            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Top Ranked Topics (Algorithm Weighted):',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                IconButton(
                  tooltip: 'Refresh Topics',
                  icon: const Icon(Icons.refresh),
                  onPressed: _fetchTopics,
                ),
              ],
            ),
            const SizedBox(height: 8),

            if (_isLoadingTopics)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (_topics.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Text(
                    'No topics found. Add seed terms to fetch trends.',
                  ),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _topics.length,
                itemBuilder: (ctx, idx) {
                  final t = _topics[idx];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: Colors.redAccent.withValues(
                          alpha: 0.2,
                        ),
                        child: Text(
                          '#${idx + 1}',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.redAccent,
                          ),
                        ),
                      ),
                      title: Text(
                        t.topic,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Row(
                        children: [
                          Text('Score: ${t.score.toStringAsFixed(2)}'),
                          const SizedBox(width: 8),
                          if (t.needsReview)
                            const Chip(
                              label: Text(
                                'Needs Review',
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.orange,
                                ),
                              ),
                              backgroundColor: Color(0x33FFA726),
                              visualDensity: VisualDensity.compact,
                            ),
                        ],
                      ),
                      trailing: ElevatedButton.icon(
                        onPressed: () => _sendTopicToStudio(t.topic),
                        icon: const Icon(Icons.auto_fix_high, size: 16),
                        label: const Text('Use Topic'),
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // TAB 2: Script Studio
  // --------------------------------------------------------------------------
  Widget _buildScriptStudioTab() {
    final wordCount = _scriptBodyController.text.trim().isEmpty
        ? 0
        : _scriptBodyController.text.trim().split(RegExp(r'\s+')).length;
    final estimatedSeconds = (wordCount / 2.5).round();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _scriptTopicController,
                          decoration: const InputDecoration(
                            labelText: 'Video Topic',
                            hintText: 'e.g. SIP Explained for Beginners',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.lightbulb_outline),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton.icon(
                        onPressed: _isGeneratingScript
                            ? null
                            : () => _generateScriptForTopic(),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            vertical: 18,
                            horizontal: 16,
                          ),
                        ),
                        icon: _isGeneratingScript
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.auto_awesome),
                        label: const Text('Generate Script'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          initialValue: _selectedVoice,
                          decoration: const InputDecoration(
                            labelText: 'TTS Voice Model',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.record_voice_over_outlined),
                          ),
                          items: _availableVoices
                              .map(
                                (v) =>
                                    DropdownMenuItem(value: v, child: Text(v)),
                              )
                              .toList(),
                          onChanged: (val) => setState(
                            () => _selectedVoice = val ?? _selectedVoice,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Chip(
                        avatar: const Icon(Icons.timer_outlined, size: 16),
                        label: Text('~${estimatedSeconds}s ($wordCount words)'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          TextField(
            controller: _scriptTitleController,
            decoration: const InputDecoration(
              labelText: 'YouTube Title (Under 60 Chars)',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.title_rounded),
            ),
          ),
          const SizedBox(height: 12),

          TextField(
            controller: _scriptDescController,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Video Description & Tags',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.description_outlined),
            ),
          ),
          const SizedBox(height: 12),

          TextField(
            controller: _scriptBodyController,
            maxLines: 10,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              labelText: 'Narration Script Body',
              hintText: 'Enter or edit narration script here...',
              border: OutlineInputBorder(),
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 16),

          Card(
            elevation: 1,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  Checkbox(
                    value: _autoPublish,
                    onChanged: (val) =>
                        setState(() => _autoPublish = val ?? false),
                  ),
                  const Text(
                    'Auto-Upload to YouTube upon Build',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 16),
                  if (_autoPublish)
                    Expanded(
                      child: DropdownButton<String>(
                        value: _autoPublishPrivacy,
                        isDense: true,
                        underline: const SizedBox(),
                        items: const [
                          DropdownMenuItem(
                            value: 'private',
                            child: Text('Private (Default / Safe)'),
                          ),
                          DropdownMenuItem(
                            value: 'unlisted',
                            child: Text('Unlisted'),
                          ),
                          DropdownMenuItem(
                            value: 'public',
                            child: Text('Public (Instant Live)'),
                          ),
                        ],
                        onChanged: (val) => setState(
                          () => _autoPublishPrivacy = val ?? 'private',
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          Wrap(
            spacing: 12,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                onPressed: () {
                  setState(() {
                    _scriptTopicController.clear();
                    _scriptTitleController.clear();
                    _scriptDescController.clear();
                    _scriptBodyController.clear();
                  });
                  _showMessage('Form cleared');
                },
                icon: const Icon(Icons.clear_all),
                label: const Text('Clear'),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  if (_scriptBodyController.text.isNotEmpty) {
                    Clipboard.setData(
                      ClipboardData(text: _scriptBodyController.text),
                    );
                    _showMessage('Script copied to clipboard');
                  }
                },
                icon: const Icon(Icons.copy),
                label: const Text('Copy Script'),
              ),
              ElevatedButton.icon(
                onPressed: _saveDraft,
                icon: const Icon(Icons.save_outlined),
                label: const Text('Save Draft'),
              ),
              ElevatedButton.icon(
                onPressed: _isBuildingVideo ? null : _buildVideoPipeline,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                ),
                icon: _isBuildingVideo
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.rocket_launch_rounded),
                label: const Text('Synthesize Voice & Build Video'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // --------------------------------------------------------------------------
  // TAB 3: Video Studio & Pipeline
  // --------------------------------------------------------------------------
  Widget _buildVideoStudioTab() {
    final filtered = _videoFilter == 'all'
        ? _videos
        : _videos.where((v) => v.status.toLowerCase() == _videoFilter).toList();

    return RefreshIndicator(
      onRefresh: _fetchVideos,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Wrap(
                  spacing: 8,
                  children: [
                    ChoiceChip(
                      label: Text('All (${_videos.length})'),
                      selected: _videoFilter == 'all',
                      onSelected: (val) => setState(() => _videoFilter = 'all'),
                    ),
                    ChoiceChip(
                      label: Text(
                        'Ready (${_videos.where((v) => v.status == "ready").length})',
                      ),
                      selected: _videoFilter == 'ready',
                      onSelected: (val) =>
                          setState(() => _videoFilter = 'ready'),
                    ),
                    ChoiceChip(
                      label: Text(
                        'Uploaded (${_videos.where((v) => v.status == "uploaded").length})',
                      ),
                      selected: _videoFilter == 'uploaded',
                      onSelected: (val) =>
                          setState(() => _videoFilter = 'uploaded'),
                    ),
                  ],
                ),
                IconButton(
                  tooltip: 'Refresh Video List',
                  icon: const Icon(Icons.refresh),
                  onPressed: _fetchVideos,
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (_isLoadingVideos)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (filtered.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(40),
                  child: Text(
                    'No videos in this category. Generate one from Script Studio!',
                  ),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: filtered.length,
                itemBuilder: (ctx, idx) {
                  final v = filtered[idx];
                  final isReady = v.status == 'ready' || v.hasVideo;
                  final isUploaded =
                      v.status == 'uploaded' || v.youtubeVideoId != null;

                  return Card(
                    elevation: 3,
                    margin: const EdgeInsets.only(bottom: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                width: 50,
                                height: 50,
                                decoration: BoxDecoration(
                                  color: isUploaded
                                      ? Colors.redAccent.withValues(alpha: 0.15)
                                      : const Color(0xFF10B981)
                                            .withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(
                                  isUploaded
                                      ? Icons.play_circle_fill_rounded
                                      : Icons.video_file_rounded,
                                  color: isUploaded
                                      ? Colors.redAccent
                                      : const Color(0xFF10B981),
                                  size: 30,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      v.title.isNotEmpty
                                          ? v.title
                                          : 'Project ${v.localId}',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                      ),
                                    ),
                                    Text(
                                      'Topic: ${v.topic} | Voice: ${v.voice}',
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: Colors.grey,
                                      ),
                                    ),
                                    if (v.youtubeVideoId != null)
                                      Text(
                                        'YouTube: ${v.youtubeVideoId} (${v.privacyStatus})',
                                        style: const TextStyle(
                                          fontSize: 12,
                                          color: Colors.redAccent,
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                              Chip(
                                label: Text(
                                  v.status.toUpperCase(),
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: isUploaded
                                        ? Colors.redAccent
                                        : const Color(0xFF10B981),
                                  ),
                                ),
                                backgroundColor: isUploaded
                                    ? Colors.redAccent.withValues(alpha: 0.1)
                                    : const Color(0xFF10B981)
                                          .withValues(alpha: 0.1),
                              ),
                            ],
                          ),
                          const Divider(height: 20),

                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton.icon(
                                onPressed: () => _showVideoDetails(v),
                                icon: const Icon(Icons.info_outline, size: 16),
                                label: const Text('Details'),
                              ),
                              const SizedBox(width: 8),
                              if (isReady && !isUploaded)
                                ElevatedButton.icon(
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.redAccent,
                                    foregroundColor: Colors.white,
                                  ),
                                  onPressed: () => _showUploadDialog(v),
                                  icon: const Icon(Icons.upload, size: 16),
                                  label: const Text('Upload to YouTube'),
                                ),
                              const SizedBox(width: 8),
                              IconButton(
                                tooltip: 'Delete',
                                icon: const Icon(
                                  Icons.delete_outline,
                                  color: Colors.grey,
                                ),
                                onPressed: () => _deleteVideo(v.localId),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // TAB 4: Analytics & Learning
  // --------------------------------------------------------------------------
  Widget _buildAnalyticsTab() {
    final topicsList = (_analyticsData['topics'] as List<dynamic>?) ?? [];
    final summary = (_analyticsData['summary'] as Map<String, dynamic>?) ?? {};

    return RefreshIndicator(
      onRefresh: _fetchAnalytics,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _buildKpiCard(
                  'Learned Topics',
                  '${topicsList.length}',
                  Icons.psychology_outlined,
                  Colors.indigo,
                ),
                const SizedBox(width: 12),
                _buildKpiCard(
                  'Average Score',
                  '${summary['avg_score'] ?? "0.50"}',
                  Icons.grade_outlined,
                  Colors.amber,
                ),
                const SizedBox(width: 12),
                _buildKpiCard(
                  'Total Attempts',
                  '${topicsList.fold<int>(0, (a, b) => a + ((b['attempts'] as int?) ?? 0))}',
                  Icons.repeat,
                  Colors.teal,
                ),
              ],
            ),
            const SizedBox(height: 16),

            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Reinforcement Learning Feedback Engine',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 15,
                            ),
                          ),
                          SizedBox(height: 4),
                          Text(
                            'Train algorithm weights based on retention, views, and subscriber conversions.',
                            style: TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                    ElevatedButton.icon(
                      onPressed: () => _showFeedbackDialog(),
                      icon: const Icon(Icons.add_chart_rounded),
                      label: const Text('Record Feedback'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            const Text(
              'Topic Performance Leaderboard:',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),

            if (topicsList.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Text('No historical performance data yet.'),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: topicsList.length,
                itemBuilder: (ctx, idx) {
                  final t = topicsList[idx];
                  final double score = (t['score'] is num)
                      ? (t['score'] as num).toDouble()
                      : 0.5;
                  final int attempts = t['attempts'] ?? 1;

                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: Colors.indigo.withValues(alpha: 0.15),
                        child: Text(
                          '${(score * 100).toInt()}%',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                            color: Colors.indigo,
                          ),
                        ),
                      ),
                      title: Text(
                        t['topic'] ?? '',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Text(
                        'Attempts: $attempts | Last Views: ${t['last_stats']?['views'] ?? "N/A"}',
                      ),
                      trailing: IconButton(
                        icon: const Icon(Icons.tune),
                        tooltip: 'Adjust Score',
                        onPressed: () => _showFeedbackDialog(t['topic']),
                      ),
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // TAB 5: Settings & Supabase Health
  // --------------------------------------------------------------------------
  Widget _buildSettingsTab() {
    if (!(_api.currentUser?.isAdmin ?? false)) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Text(
            'Administrator access is required to change system settings.',
          ),
        ),
      );
    }
    final dbStatus = _api.dbStatus;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Supabase Database',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 8),
                  Text('Database: ${dbStatus?.dialect ?? "Supabase Postgres"}'),
                  Text('Provider: ${dbStatus?.url ?? "Supabase"}'),
                  Text('Status: ${dbStatus?.message ?? "Healthy"}'),
                  const SizedBox(height: 12),
                  ElevatedButton.icon(
                    onPressed: () => _api.fetchDbStatus().then((_) {
                      _showMessage('Database status refreshed');
                      setState(() {});
                    }),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Refresh DB Health'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Channel & Pipeline Configuration',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _channelNameController,
                    decoration: const InputDecoration(
                      labelText: 'Channel Name',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _targetSecondsController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Target Video Duration (seconds; up to 600)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _pexelsKeyController,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Pexels API Key (Free Stock Footage)',
                      hintText: 'Leave empty to keep existing key',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.key),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      foregroundColor: Colors.white,
                    ),
                    onPressed: _saveSettings,
                    icon: const Icon(Icons.save),
                    label: const Text('Save Settings'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildKpiCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Card(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color, size: 24),
              const SizedBox(height: 8),
              Text(
                value,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
              Text(
                label,
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
