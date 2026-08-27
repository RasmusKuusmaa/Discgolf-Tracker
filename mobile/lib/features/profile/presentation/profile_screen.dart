import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_exception.dart';
import '../../../core/widgets/confirmation_dialog.dart';
import '../../../domain/models/auth_state.dart';
import '../../../domain/models/user.dart';
import '../../auth/providers/auth_controller.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final TextEditingController _displayNameController = TextEditingController();
  final TextEditingController _homeCityController = TextEditingController();

  User? _loadedFor;
  String _profileVisibility = 'public';
  String _statsVisibility = 'public';
  bool _allowFriendRequests = true;
  bool _isSaving = false;

  @override
  void dispose() {
    _displayNameController.dispose();
    _homeCityController.dispose();
    super.dispose();
  }

  void _syncFromUser(User user) {
    if (_loadedFor == user) {
      return;
    }
    _loadedFor = user;
    _displayNameController.text = user.displayName;
    _homeCityController.text = user.homeCity ?? '';
    _profileVisibility = user.profileVisibility;
    _statsVisibility = user.statsVisibility;
    _allowFriendRequests = user.allowFriendRequests;
  }

  Future<void> _save() async {
    setState(() => _isSaving = true);
    try {
      await ref
          .read(authControllerProvider.notifier)
          .updateProfile(
            displayName: _displayNameController.text.trim(),
            homeCity: _homeCityController.text.trim().isEmpty
                ? null
                : _homeCityController.text.trim(),
            profileVisibility: _profileVisibility,
            statsVisibility: _statsVisibility,
            allowFriendRequests: _allowFriendRequests,
          );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(const SnackBar(content: Text('Profile updated')));
    } on ApiException catch (exception) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(exception.message)));
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _logout() async {
    final bool confirmed = await showConfirmationDialog(
      context,
      title: 'Log out',
      message: 'You will need to sign in again to keep tracking rounds.',
      confirmText: 'Log out',
      isDestructive: true,
    );
    if (confirmed) {
      await ref.read(authControllerProvider.notifier).logout();
    }
  }

  @override
  Widget build(BuildContext context) {
    final AuthState authState = ref.watch(authControllerProvider);
    if (authState is! AuthAuthenticated) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    _syncFromUser(authState.user);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Log out',
            onPressed: _isSaving ? null : _logout,
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Center(child: _Avatar(user: authState.user)),
            const SizedBox(height: 8),
            Center(
              child: Text(
                '@${authState.user.username}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _displayNameController,
              enabled: !_isSaving,
              decoration: const InputDecoration(labelText: 'Display name'),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _homeCityController,
              enabled: !_isSaving,
              decoration: const InputDecoration(labelText: 'Home city'),
            ),
            const SizedBox(height: 24),
            Text('Profile visibility', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            _VisibilitySelector(
              value: _profileVisibility,
              enabled: !_isSaving,
              onChanged: (value) => setState(() => _profileVisibility = value),
            ),
            const SizedBox(height: 16),
            Text('Stats visibility', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            _VisibilitySelector(
              value: _statsVisibility,
              enabled: !_isSaving,
              onChanged: (value) => setState(() => _statsVisibility = value),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Allow friend requests'),
              value: _allowFriendRequests,
              onChanged: _isSaving
                  ? null
                  : (bool value) => setState(() => _allowFriendRequests = value),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _isSaving ? null : _save,
              child: _isSaving
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Save changes'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.user});

  final User user;

  @override
  Widget build(BuildContext context) {
    final String? avatarUrl = user.avatarUrl;
    return CircleAvatar(
      radius: 40,
      backgroundImage: avatarUrl != null ? NetworkImage(avatarUrl) : null,
      child: avatarUrl == null ? Text(_initials(user.displayName)) : null,
    );
  }

  String _initials(String displayName) {
    final List<String> parts = displayName
        .trim()
        .split(RegExp(r'\s+'))
        .where((String part) => part.isNotEmpty)
        .toList();
    if (parts.isEmpty) {
      return '?';
    }
    if (parts.length == 1) {
      return parts.first.substring(0, 1).toUpperCase();
    }
    return (parts.first.substring(0, 1) + parts.last.substring(0, 1)).toUpperCase();
  }
}

class _VisibilitySelector extends StatelessWidget {
  const _VisibilitySelector({
    required this.value,
    required this.enabled,
    required this.onChanged,
  });

  final String value;
  final bool enabled;
  final ValueChanged<String> onChanged;

  static const List<(String, String)> _options = [
    ('public', 'Public'),
    ('friends', 'Friends'),
    ('private', 'Private'),
  ];

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<String>(
      segments: [
        for (final (String optionValue, String label) in _options)
          ButtonSegment<String>(value: optionValue, label: Text(label)),
      ],
      selected: <String>{value},
      onSelectionChanged: enabled
          ? (Set<String> selection) => onChanged(selection.first)
          : null,
    );
  }
}
