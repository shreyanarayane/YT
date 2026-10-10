import 'package:flutter_test/flutter_test.dart';
import 'package:youtube_manager_ui/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const YouTubeAgentApp());
    expect(find.text('AI YouTube Manager'), findsOneWidget);
  });
}
