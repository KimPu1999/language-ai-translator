import 'package:flutter/material.dart';

import '../collections/empty_collection_page.dart';

class FavoritesPage extends StatelessWidget {
  const FavoritesPage({super.key});
  @override
  Widget build(BuildContext context) => const EmptyCollectionPage(type: 'favorites');
}

