import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/localization/app_strings.dart';
import '../../core/network/api_client.dart';
import '../../core/providers/app_providers.dart';
import '../../core/theme/app_theme.dart';

class AuthScaffold extends ConsumerWidget {
  const AuthScaffold({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings(Localizations.localeOf(context));
    final themeMode = ref.watch(themeModeProvider);
    final locale = ref.watch(localeProvider);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: ListView(padding: const EdgeInsets.fromLTRB(20, 20, 20, 32), children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                TextButton.icon(onPressed: () => context.go('/text'), icon: const Icon(Icons.auto_awesome_rounded), label: Text(strings.appName, style: const TextStyle(fontWeight: FontWeight.w800))),
                Row(children: [
                  IconButton(tooltip: strings.toggleTheme, onPressed: () => ref.read(themeModeProvider.notifier).state = themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark, icon: Icon(themeMode == ThemeMode.dark ? Icons.light_mode_outlined : Icons.dark_mode_outlined)),
                  TextButton(onPressed: () => ref.read(localeProvider.notifier).state = Locale(locale.languageCode == 'my' ? 'en' : 'my'), child: Text(locale.languageCode == 'my' ? 'EN' : 'MM')),
                ]),
              ]),
              const SizedBox(height: 36),
              child,
            ]),
          ),
        ),
      ),
    );
  }
}

class AuthCard extends StatelessWidget {
  const AuthCard({super.key, required this.eyebrow, required this.title, required this.copy, required this.child});
  final String eyebrow;
  final String title;
  final String copy;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(eyebrow.toUpperCase(), style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppTheme.blue, fontWeight: FontWeight.w800, letterSpacing: 1.4)),
            const SizedBox(height: 10),
            Text(title, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Text(copy, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, height: 1.5)),
            const SizedBox(height: 24),
            child,
          ]),
        ),
      );
}

class AuthTextField extends StatefulWidget {
  const AuthTextField({super.key, required this.label, required this.controller, this.keyboardType, this.autofillHints, this.obscure = false});
  final String label;
  final TextEditingController controller;
  final TextInputType? keyboardType;
  final Iterable<String>? autofillHints;
  final bool obscure;

  @override
  State<AuthTextField> createState() => _AuthTextFieldState();
}

class _AuthTextFieldState extends State<AuthTextField> {
  late bool _obscure = widget.obscure;

  @override
  Widget build(BuildContext context) => TextField(
        controller: widget.controller,
        obscureText: _obscure,
        keyboardType: widget.keyboardType,
        autofillHints: widget.autofillHints,
        textInputAction: TextInputAction.next,
        decoration: InputDecoration(labelText: widget.label, suffixIcon: widget.obscure ? IconButton(tooltip: _obscure ? 'Show password' : 'Hide password', onPressed: () => setState(() => _obscure = !_obscure), icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined)) : null),
      );
}

class AuthError extends StatelessWidget {
  const AuthError({super.key, required this.message});
  final String message;
  @override
  Widget build(BuildContext context) => Container(width: double.infinity, padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: Theme.of(context).colorScheme.errorContainer, borderRadius: BorderRadius.circular(14)), child: Text(message, style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer)));
}

class AuthSubmit extends StatelessWidget {
  const AuthSubmit({super.key, required this.label, required this.busy, required this.onPressed});
  final String label;
  final bool busy;
  final VoidCallback? onPressed;
  @override
  Widget build(BuildContext context) => SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: busy ? null : onPressed, icon: busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.arrow_forward_rounded), label: Text(label)));
}

class AuthGate extends ConsumerWidget {
  const AuthGate({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    if (auth.status == AuthStatus.loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (!auth.isAuthenticated) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return child;
  }
}

class AuthLifecycle extends ConsumerStatefulWidget {
  const AuthLifecycle({super.key, required this.child});
  final Widget child;
  @override
  ConsumerState<AuthLifecycle> createState() => _AuthLifecycleState();
}

class _AuthLifecycleState extends ConsumerState<AuthLifecycle> with WidgetsBindingObserver {
  @override
  void initState() { super.initState(); WidgetsBinding.instance.addObserver(this); }
  @override
  void dispose() { WidgetsBinding.instance.removeObserver(this); super.dispose(); }
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) { if (state == AppLifecycleState.resumed) ref.read(authProvider.notifier).validateSession(); }
  @override
  Widget build(BuildContext context) => widget.child;
}

class SignInPage extends ConsumerStatefulWidget {
  const SignInPage({super.key});
  @override
  ConsumerState<SignInPage> createState() => _SignInPageState();
}

class _SignInPageState extends ConsumerState<SignInPage> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  String? _validationError;

  @override
  void dispose() { _email.dispose(); _password.dispose(); super.dispose(); }

  Future<void> _submit() async {
    final strings = AppStrings(Localizations.localeOf(context));
    setState(() => _validationError = _email.text.trim().contains('@') && _password.text.isNotEmpty ? null : strings.validCredentials);
    if (_validationError != null) return;
    final success = await ref.read(authProvider.notifier).login(email: _email.text.trim(), password: _password.text);
    if (success && mounted) context.go('/text');
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings(Localizations.localeOf(context));
    final auth = ref.watch(authProvider);
    final error = _validationError ?? auth.error;
    return AuthScaffold(child: AuthCard(eyebrow: strings.signInEyebrow, title: strings.signIn, copy: strings.signInBody, child: AutofillGroup(child: Column(children: [AuthTextField(label: strings.email, controller: _email, keyboardType: TextInputType.emailAddress, autofillHints: const [AutofillHints.username]), const SizedBox(height: 14), AuthTextField(label: strings.password, controller: _password, obscure: true, autofillHints: const [AutofillHints.password]), if (error != null) ...[const SizedBox(height: 14), AuthError(message: error)], const SizedBox(height: 20), AuthSubmit(label: strings.signIn, busy: auth.status == AuthStatus.loading, onPressed: _submit), const SizedBox(height: 14), Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [TextButton(onPressed: () => context.go('/auth/forgot-password'), child: Text(strings.forgotPassword)), TextButton(onPressed: () => context.go('/auth/register'), child: Text(strings.createAccount))])]))));
  }
}

class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});
  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  String? _error;
  bool _done = false;
  @override
  void dispose() { _email.dispose(); _password.dispose(); _confirm.dispose(); super.dispose(); }
  Future<void> _submit() async {
    final strings = AppStrings(Localizations.localeOf(context));
    if (!_email.text.trim().contains('@')) return setState(() => _error = strings.validCredentials);
    if (_password.text.length < 8 || _password.text.length > 12) return setState(() => _error = strings.passwordRule);
    if (_password.text != _confirm.text) return setState(() => _error = strings.passwordsMustMatch);
    setState(() { _busy = true; _error = null; });
    try { await ref.read(apiClientProvider).register(email: _email.text.trim(), password: _password.text); if (mounted) setState(() => _done = true); } on ApiFailure catch (error) { if (mounted) setState(() => _error = error.message); } finally { if (mounted) setState(() => _busy = false); }
  }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return AuthScaffold(child: AuthCard(eyebrow: strings.registration, title: _done ? strings.checkYourEmail : strings.createAccount, copy: _done ? strings.verificationSent : strings.registerBody, child: _done ? Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(strings.verificationSentDetail), const SizedBox(height: 20), TextButton(onPressed: () => context.go('/auth/sign-in'), child: Text(strings.backToSignIn))]) : Column(children: [AuthTextField(label: strings.email, controller: _email, keyboardType: TextInputType.emailAddress), const SizedBox(height: 14), AuthTextField(label: strings.password, controller: _password, obscure: true), const SizedBox(height: 14), AuthTextField(label: strings.confirmPassword, controller: _confirm, obscure: true), if (_error != null) ...[const SizedBox(height: 14), AuthError(message: _error!)], const SizedBox(height: 8), Text(strings.passwordRule, style: Theme.of(context).textTheme.bodySmall), const SizedBox(height: 16), AuthSubmit(label: strings.createAccount, busy: _busy, onPressed: _submit), TextButton(onPressed: () => context.go('/auth/sign-in'), child: Text(strings.alreadyHaveAccount))]))); }
}

class VerifyEmailPage extends ConsumerStatefulWidget {
  const VerifyEmailPage({super.key, this.initialToken});
  final String? initialToken;
  @override
  ConsumerState<VerifyEmailPage> createState() => _VerifyEmailPageState();
}

class _VerifyEmailPageState extends ConsumerState<VerifyEmailPage> {
  late final _token = TextEditingController(text: widget.initialToken ?? '');
  final _email = TextEditingController();
  bool _busy = false;
  String? _error;
  bool _done = false;
  @override
  void dispose() { _token.dispose(); _email.dispose(); super.dispose(); }
  Future<void> _submit() async { final strings = AppStrings(Localizations.localeOf(context)); if (_token.text.isEmpty && !_email.text.trim().contains('@')) return setState(() => _error = strings.validCredentials); setState(() { _busy = true; _error = null; }); try { if (_token.text.isNotEmpty) await ref.read(apiClientProvider).verifyEmail(_token.text.trim()); else await ref.read(apiClientProvider).resendVerification(_email.text.trim()); if (mounted) setState(() => _done = true); } on ApiFailure catch (error) { if (mounted) setState(() => _error = error.message); } finally { if (mounted) setState(() => _busy = false); } }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); final hasToken = _token.text.isNotEmpty; return AuthScaffold(child: AuthCard(eyebrow: strings.verification, title: _done ? strings.emailVerified : strings.verifyEmail, copy: _done ? strings.emailVerifiedBody : strings.verifyEmailBody, child: Column(children: [if (hasToken) AuthTextField(label: strings.verificationToken, controller: _token) else ...[AuthTextField(label: strings.email, controller: _email, keyboardType: TextInputType.emailAddress), const SizedBox(height: 8), Text(strings.verificationResendHint, style: Theme.of(context).textTheme.bodySmall)], if (_error != null) ...[const SizedBox(height: 14), AuthError(message: _error!)], const SizedBox(height: 20), AuthSubmit(label: hasToken ? strings.verifyEmail : strings.resendVerification, busy: _busy, onPressed: _submit), TextButton(onPressed: () => context.go('/auth/sign-in'), child: Text(strings.backToSignIn))]))); }
}

class ForgotPasswordPage extends ConsumerStatefulWidget {
  const ForgotPasswordPage({super.key});
  @override
  ConsumerState<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends ConsumerState<ForgotPasswordPage> {
  final _email = TextEditingController();
  bool _busy = false;
  bool _done = false;
  String? _error;
  @override
  void dispose() { _email.dispose(); super.dispose(); }
  Future<void> _submit() async { final strings = AppStrings(Localizations.localeOf(context)); if (!_email.text.trim().contains('@')) return setState(() => _error = strings.validCredentials); setState(() { _busy = true; _error = null; }); try { await ref.read(apiClientProvider).forgotPassword(_email.text.trim()); if (mounted) setState(() => _done = true); } on ApiFailure catch (error) { if (mounted) setState(() => _error = error.message); } finally { if (mounted) setState(() => _busy = false); } }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return AuthScaffold(child: AuthCard(eyebrow: strings.accountRecovery, title: _done ? strings.resetInstructionsSent : strings.forgotPassword, copy: _done ? strings.resetInstructionsDetail : strings.forgotPasswordBody, child: Column(children: [AuthTextField(label: strings.email, controller: _email, keyboardType: TextInputType.emailAddress), if (_error != null) ...[const SizedBox(height: 14), AuthError(message: _error!)], if (!_done) ...[const SizedBox(height: 20), AuthSubmit(label: strings.sendInstructions, busy: _busy, onPressed: _submit)], TextButton(onPressed: () => context.go('/auth/sign-in'), child: Text(strings.backToSignIn))]))); }
}

class ResetPasswordPage extends ConsumerStatefulWidget {
  const ResetPasswordPage({super.key, this.initialToken});
  final String? initialToken;
  @override
  ConsumerState<ResetPasswordPage> createState() => _ResetPasswordPageState();
}

class _ResetPasswordPageState extends ConsumerState<ResetPasswordPage> {
  late final _token = TextEditingController(text: widget.initialToken ?? '');
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  bool _done = false;
  String? _error;
  @override
  void dispose() { _token.dispose(); _password.dispose(); _confirm.dispose(); super.dispose(); }
  Future<void> _submit() async { final strings = AppStrings(Localizations.localeOf(context)); if (_token.text.trim().isEmpty) return setState(() => _error = strings.resetTokenRequired); if (_password.text.length < 8 || _password.text.length > 12) return setState(() => _error = strings.passwordRule); if (_password.text != _confirm.text) return setState(() => _error = strings.passwordsMustMatch); setState(() { _busy = true; _error = null; }); try { await ref.read(apiClientProvider).resetPassword(token: _token.text.trim(), password: _password.text); if (mounted) setState(() => _done = true); } on ApiFailure catch (error) { if (mounted) setState(() => _error = error.message); } finally { if (mounted) setState(() => _busy = false); } }
  @override
  Widget build(BuildContext context) { final strings = AppStrings(Localizations.localeOf(context)); return AuthScaffold(child: AuthCard(eyebrow: strings.accountRecovery, title: _done ? strings.passwordReset : strings.resetPassword, copy: _done ? strings.passwordResetBody : strings.resetPasswordBody, child: Column(children: [if (widget.initialToken == null) AuthTextField(label: strings.verificationToken, controller: _token), if (widget.initialToken == null) const SizedBox(height: 14), if (!_done) ...[AuthTextField(label: strings.newPassword, controller: _password, obscure: true), const SizedBox(height: 14), AuthTextField(label: strings.confirmPassword, controller: _confirm, obscure: true), if (_error != null) ...[const SizedBox(height: 14), AuthError(message: _error!)], const SizedBox(height: 20), AuthSubmit(label: strings.resetPassword, busy: _busy, onPressed: _submit)], if (_done) TextButton(onPressed: () => context.go('/auth/sign-in'), child: Text(strings.backToSignIn))]))); }
}
