import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SavedTranslation {
  const SavedTranslation({required this.id, required this.sourceLanguage, required this.targetLanguage, required this.sourceText, required this.translatedText, required this.createdAt, this.updatedAt});

  factory SavedTranslation.fromJson(Map<String, dynamic> json) => SavedTranslation(
        id: json['id'] as String,
        sourceLanguage: json['source_language'] as String,
        targetLanguage: json['target_language'] as String,
        sourceText: json['source_text'] as String,
        translatedText: json['translated_text'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: json['updated_at'] == null ? null : DateTime.tryParse(json['updated_at'] as String),
      );

  final String id;
  final String sourceLanguage;
  final String targetLanguage;
  final String sourceText;
  final String translatedText;
  final DateTime createdAt;
  final DateTime? updatedAt;

  Map<String, dynamic> toJson() => {
        'id': id,
        'source_language': sourceLanguage,
        'target_language': targetLanguage,
        'source_text': sourceText,
        'translated_text': translatedText,
        'created_at': createdAt.toIso8601String(),
        if (updatedAt != null) 'updated_at': updatedAt!.toIso8601String(),
      };
}

class LocalLibraryState {
  const LocalLibraryState({this.enabled = false, this.history = const [], this.favorites = const [], this.isLoading = true});

  final bool enabled;
  final List<SavedTranslation> history;
  final List<SavedTranslation> favorites;
  final bool isLoading;

  LocalLibraryState copyWith({bool? enabled, List<SavedTranslation>? history, List<SavedTranslation>? favorites, bool? isLoading}) => LocalLibraryState(enabled: enabled ?? this.enabled, history: history ?? this.history, favorites: favorites ?? this.favorites, isLoading: isLoading ?? this.isLoading);
}

class LocalLibraryController extends StateNotifier<LocalLibraryState> {
  LocalLibraryController() : super(const LocalLibraryState()) {
    _load();
  }

  static const _enabledKey = 'lingua-local-library-enabled';
  static const _historyKey = 'lingua-local-history';
  static const _favoritesKey = 'lingua-local-favorites';
  SharedPreferences? _preferences;

  Future<void> _load() async {
    try {
      final preferences = await SharedPreferences.getInstance();
      _preferences = preferences;
      final enabled = preferences.getBool(_enabledKey) ?? false;
      state = state.copyWith(enabled: enabled, history: enabled ? _decode(preferences.getStringList(_historyKey)) : const [], favorites: enabled ? _decode(preferences.getStringList(_favoritesKey)) : const [], isLoading: false);
    } catch (_) {
      state = state.copyWith(isLoading: false);
    }
  }

  List<SavedTranslation> _decode(List<String>? values) => (values ?? const []).map((value) => SavedTranslation.fromJson(jsonDecode(value) as Map<String, dynamic>)).toList();

  Future<void> setEnabled(bool enabled) async {
    state = state.copyWith(enabled: enabled, history: enabled ? state.history : const [], favorites: enabled ? state.favorites : const []);
    final preferences = _preferences ?? await SharedPreferences.getInstance();
    _preferences = preferences;
    await preferences.setBool(_enabledKey, enabled);
    if (!enabled) {
      await preferences.remove(_historyKey);
      await preferences.remove(_favoritesKey);
    }
  }

  Future<void> save(SavedTranslation item) async {
    if (!state.enabled) return;
    final items = [item, ...state.history.where((entry) => entry.id != item.id)].take(50).toList();
    state = state.copyWith(history: items);
    await _persist(_historyKey, items);
  }

  Future<void> toggleFavorite(SavedTranslation item) async {
    if (!state.enabled) return;
    final exists = state.favorites.any((entry) => entry.id == item.id);
    final items = exists ? state.favorites.where((entry) => entry.id != item.id).toList() : [item, ...state.favorites].take(50).toList();
    state = state.copyWith(favorites: items);
    await _persist(_favoritesKey, items);
  }

  Future<void> clearPrivateData() async {
    state = state.copyWith(history: const [], favorites: const []);
    final preferences = _preferences ?? await SharedPreferences.getInstance();
    _preferences = preferences;
    await preferences.remove(_historyKey);
    await preferences.remove(_favoritesKey);
  }

  Future<void> mergeSynced({required List<SavedTranslation> translations, required List<String> deletedIds, required List<String> favoriteIds}) async {
    if (!state.enabled) return;
    final deleted = deletedIds.toSet();
    final merged = <String, SavedTranslation>{for (final item in state.history) item.id: item};
    for (final item in translations) { merged[item.id] = item; }
    merged.removeWhere((key, _) => deleted.contains(key));
    final ordered = merged.values.take(50).toList();
    final favoriteSet = favoriteIds.toSet();
    final favorites = favoriteIds.isEmpty ? state.favorites.where((item) => !deleted.contains(item.id)).toList() : ordered.where((item) => favoriteSet.contains(item.id)).toList();
    state = state.copyWith(history: ordered, favorites: favorites.take(50).toList());
    await _persist(_historyKey, ordered);
    await _persist(_favoritesKey, favorites.take(50).toList());
  }

  Future<void> _persist(String key, List<SavedTranslation> items) async {
    final preferences = _preferences ?? await SharedPreferences.getInstance();
    _preferences = preferences;
    await preferences.setStringList(key, items.map((item) => jsonEncode(item.toJson())).toList());
  }
}

final localLibraryProvider = StateNotifierProvider<LocalLibraryController, LocalLibraryState>((ref) => LocalLibraryController());
