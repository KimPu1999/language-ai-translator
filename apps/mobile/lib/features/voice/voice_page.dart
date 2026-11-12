import 'package:flutter/material.dart';

import '../../widgets/feature_unavailable.dart';

class VoicePage extends StatelessWidget {
  const VoicePage({super.key});
  @override
  Widget build(BuildContext context) => const FeatureUnavailable(icon: Icons.mic_none_rounded, title: 'Voice');
}

