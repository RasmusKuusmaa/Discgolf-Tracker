import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/network/network_providers.dart';
import '../../../domain/models/auth_state.dart';
import '../providers/auth_controller.dart';

enum _UsernameCheck { idle, checking, available, taken, unknown }

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  static final RegExp _usernamePattern = RegExp(r'^[a-zA-Z0-9_]+$');
  static final RegExp _emailPattern = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
  static final RegExp _hasLetter = RegExp('[A-Za-z]');
  static final RegExp _hasDigit = RegExp('[0-9]');

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _displayNameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController = TextEditingController();

  bool _obscurePassword = true;
  String _password = '';
  Timer? _usernameDebounce;
  int _usernameCheckToken = 0;
  _UsernameCheck _usernameCheck = _UsernameCheck.idle;

  @override
  void initState() {
    super.initState();
    _passwordController.addListener(() {
      setState(() => _password = _passwordController.text);
    });
  }

  @override
  void dispose() {
    _usernameDebounce?.cancel();
    _emailController.dispose();
    _usernameController.dispose();
    _displayNameController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  void _onUsernameChanged(String value) {
    _usernameDebounce?.cancel();
    final String candidate = value.trim();
    if (candidate.length < 3 || !_usernamePattern.hasMatch(candidate)) {
      setState(() => _usernameCheck = _UsernameCheck.idle);
      return;
    }

    setState(() => _usernameCheck = _UsernameCheck.checking);
    final int token = ++_usernameCheckToken;
    _usernameDebounce = Timer(const Duration(milliseconds: 500), () async {
      try {
        final bool available = await ref
            .read(usersApiProvider)
            .isUsernameAvailable(candidate);
        if (!mounted || token != _usernameCheckToken) {
          return;
        }
        setState(() {
          _usernameCheck = available ? _UsernameCheck.available : _UsernameCheck.taken;
        });
      } on ApiException {
        if (!mounted || token != _usernameCheckToken) {
          return;
        }
        setState(() => _usernameCheck = _UsernameCheck.unknown);
      }
    });
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    ref
        .read(authControllerProvider.notifier)
        .register(
          email: _emailController.text.trim(),
          username: _usernameController.text.trim(),
          displayName: _displayNameController.text.trim(),
          password: _passwordController.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<AuthState>(authControllerProvider, (previous, next) {
      if (next case AuthError(:final message)) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(message)));
      }
    });

    final AuthState authState = ref.watch(authControllerProvider);
    final bool isSubmitting = authState is AuthAuthenticating;

    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextFormField(
                      controller: _emailController,
                      enabled: !isSubmitting,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(labelText: 'Email'),
                      validator: (value) {
                        final String candidate = value?.trim() ?? '';
                        if (candidate.isEmpty) {
                          return 'Enter your email';
                        }
                        if (!_emailPattern.hasMatch(candidate)) {
                          return 'Enter a valid email address';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _usernameController,
                      enabled: !isSubmitting,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Username',
                        helperText: '3-32 characters: letters, numbers, underscore',
                        suffixIcon: _usernameStatusIcon(context),
                      ),
                      onChanged: _onUsernameChanged,
                      validator: (value) {
                        final String candidate = value?.trim() ?? '';
                        if (candidate.length < 3 || candidate.length > 32) {
                          return 'Username must be 3-32 characters';
                        }
                        if (!_usernamePattern.hasMatch(candidate)) {
                          return 'Only letters, numbers and underscore allowed';
                        }
                        if (_usernameCheck == _UsernameCheck.taken) {
                          return 'That username is already taken';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _displayNameController,
                      enabled: !isSubmitting,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(labelText: 'Display name'),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Enter a display name';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _passwordController,
                      enabled: !isSubmitting,
                      obscureText: _obscurePassword,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Password',
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                          ),
                          onPressed: () {
                            setState(() => _obscurePassword = !_obscurePassword);
                          },
                        ),
                      ),
                      validator: (value) {
                        final String candidate = value ?? '';
                        if (candidate.length < 8 || candidate.length > 128) {
                          return 'Password must be 8-128 characters';
                        }
                        if (!_hasLetter.hasMatch(candidate) || !_hasDigit.hasMatch(candidate)) {
                          return 'Password needs at least one letter and one number';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 8),
                    _PasswordRulesChecklist(password: _password),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _confirmPasswordController,
                      enabled: !isSubmitting,
                      obscureText: _obscurePassword,
                      textInputAction: TextInputAction.done,
                      decoration: const InputDecoration(labelText: 'Confirm password'),
                      validator: (value) {
                        if (value != _passwordController.text) {
                          return 'Passwords do not match';
                        }
                        return null;
                      },
                      onFieldSubmitted: (_) => _submit(),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: isSubmitting ? null : _submit,
                      child: isSubmitting
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Create account'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget? _usernameStatusIcon(BuildContext context) {
    switch (_usernameCheck) {
      case _UsernameCheck.idle:
      case _UsernameCheck.unknown:
        return null;
      case _UsernameCheck.checking:
        return const Padding(
          padding: EdgeInsets.all(12),
          child: SizedBox(
            height: 16,
            width: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        );
      case _UsernameCheck.available:
        return Icon(Icons.check_circle, color: Theme.of(context).colorScheme.primary);
      case _UsernameCheck.taken:
        return Icon(Icons.cancel, color: Theme.of(context).colorScheme.error);
    }
  }
}

class _PasswordRulesChecklist extends StatelessWidget {
  const _PasswordRulesChecklist({required this.password});

  final String password;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _rule(context, 'At least 8 characters', password.length >= 8),
        _rule(context, 'Contains a letter', RegExp('[A-Za-z]').hasMatch(password)),
        _rule(context, 'Contains a number', RegExp('[0-9]').hasMatch(password)),
      ],
    );
  }

  Widget _rule(BuildContext context, String label, bool met) {
    final Color color = met
        ? Theme.of(context).colorScheme.primary
        : Theme.of(context).colorScheme.onSurfaceVariant;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(met ? Icons.check_circle_outline : Icons.circle_outlined, size: 16, color: color),
          const SizedBox(width: 8),
          Text(label, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: color)),
        ],
      ),
    );
  }
}
