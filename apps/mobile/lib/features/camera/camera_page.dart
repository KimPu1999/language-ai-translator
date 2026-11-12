import 'package:flutter/material.dart';

import '../../widgets/feature_unavailable.dart';

class CameraPage extends StatelessWidget {
  const CameraPage({super.key});
  @override
  Widget build(BuildContext context) => const FeatureUnavailable(icon: Icons.camera_alt_outlined, title: 'Camera');
}

