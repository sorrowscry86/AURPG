import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:aurpg_gui/main.dart';

void main() {
  testWidgets('App renders without crashing', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: AurpgApp()));
    expect(find.byType(MaterialApp), findsOneWidget);
    expect(find.byType(Router), findsOneWidget);
  });
}
