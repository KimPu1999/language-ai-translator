import 'package:flutter/material.dart';

import '../../widgets/feature_unavailable.dart';

class DocumentsPage extends StatelessWidget {
  const DocumentsPage({super.key});
  @override
  Widget build(BuildContext context) => const FeatureUnavailable(icon: Icons.description_outlined, title: 'Documents');
}

