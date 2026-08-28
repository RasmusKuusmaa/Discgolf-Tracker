import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/loading_indicator.dart';
import '../../../domain/models/course.dart';
import '../../../domain/models/hole.dart';
import '../../../domain/models/layout.dart';
import '../providers/course_detail_controller.dart';
import '../providers/course_detail_state.dart';

class CourseDetailScreen extends ConsumerWidget {
  const CourseDetailScreen({super.key, required this.courseId});

  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final CourseDetailState state = ref.watch(
      courseDetailControllerProvider(courseId),
    );
    final Course? course = state.course;

    return Scaffold(
      appBar: AppBar(title: Text(course?.name ?? 'Course')),
      body: SafeArea(child: _buildBody(context, ref, state)),
    );
  }

  Widget _buildBody(
    BuildContext context,
    WidgetRef ref,
    CourseDetailState state,
  ) {
    final Course? course = state.course;
    if (course == null) {
      if (state.isLoading) {
        return const LoadingIndicator(message: 'Loading course…');
      }
      return const EmptyState(
        icon: Icons.golf_course_outlined,
        title: 'Course not found',
        message:
            'This course isn\'t in your local cache and could not be loaded.',
      );
    }

    final Layout? selectedLayout = course.layouts.isEmpty
        ? null
        : course.layouts.firstWhere(
            (layout) => layout.id == state.selectedLayoutId,
            orElse: () => course.layouts.first,
          );

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        _CourseHeader(course: course),
        if (course.layouts.length > 1) ...[
          const SizedBox(height: 20),
          Text('Layout', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final Layout layout in course.layouts)
                ChoiceChip(
                  label: Text(layout.name),
                  selected: layout.id == state.selectedLayoutId,
                  onSelected: (_) => ref
                      .read(courseDetailControllerProvider(courseId).notifier)
                      .selectLayout(layout.id),
                ),
            ],
          ),
        ],
        if (selectedLayout != null) ...[
          const SizedBox(height: 20),
          _BestScoreCard(bestScoreToPar: state.bestScoreToPar),
          const SizedBox(height: 20),
          Text('Holes', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          _HoleTable(holes: selectedLayout.holes),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.play_arrow),
              label: const Text('Start round'),
              onPressed: () {
                ScaffoldMessenger.of(context)
                  ..hideCurrentSnackBar()
                  ..showSnackBar(
                    const SnackBar(
                      content: Text('Round scoring is coming soon.'),
                    ),
                  );
              },
            ),
          ),
        ] else ...[
          const SizedBox(height: 20),
          const EmptyState(
            icon: Icons.format_list_numbered_outlined,
            title: 'No layouts yet',
            message: 'This course doesn\'t have any layouts to play.',
          ),
        ],
      ],
    );
  }
}

class _CourseHeader extends StatelessWidget {
  const _CourseHeader({required this.course});

  final Course course;

  @override
  Widget build(BuildContext context) {
    final String location = [
      course.city,
      course.country,
    ].where((part) => part != null && part.isNotEmpty).join(', ');
    final TextTheme textTheme = Theme.of(context).textTheme;
    final ColorScheme colorScheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (location.isNotEmpty)
          Text(
            location,
            style: textTheme.bodyMedium?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
        if (course.description != null && course.description!.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(course.description!, style: textTheme.bodyMedium),
        ],
      ],
    );
  }
}

class _BestScoreCard extends StatelessWidget {
  const _BestScoreCard({required this.bestScoreToPar});

  final int? bestScoreToPar;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.emoji_events_outlined, color: colorScheme.primary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Your best score',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  Text(
                    bestScoreToPar == null
                        ? 'No rounds played yet'
                        : _format(bestScoreToPar!),
                    style: Theme.of(context).textTheme.bodyMedium
                        ?.copyWith(color: colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _format(int scoreToPar) {
    if (scoreToPar == 0) {
      return 'Even par';
    }
    return scoreToPar > 0 ? '+$scoreToPar' : '$scoreToPar';
  }
}

class _HoleTable extends StatelessWidget {
  const _HoleTable({required this.holes});

  final List<Hole> holes;

  @override
  Widget build(BuildContext context) {
    if (holes.isEmpty) {
      return const EmptyState(icon: Icons.flag_outlined, title: 'No holes yet');
    }
    final List<Hole> sorted = [...holes]
      ..sort((a, b) => a.number.compareTo(b.number));
    final TextTheme textTheme = Theme.of(context).textTheme;
    final ColorScheme colorScheme = Theme.of(context).colorScheme;

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Column(
          children: [
            _HoleRow(
              number: 'Hole',
              par: 'Par',
              distance: 'Distance',
              style: textTheme.labelMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const Divider(height: 1),
            for (final Hole hole in sorted)
              _HoleRow(
                number: '${hole.number}',
                par: '${hole.par}',
                distance: hole.distanceM == null
                    ? '—'
                    : '${hole.distanceM!.round()} m',
                style: textTheme.bodyMedium,
              ),
          ],
        ),
      ),
    );
  }
}

class _HoleRow extends StatelessWidget {
  const _HoleRow({
    required this.number,
    required this.par,
    required this.distance,
    this.style,
  });

  final String number;
  final String par;
  final String distance;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(flex: 2, child: Text(number, style: style)),
          Expanded(flex: 2, child: Text(par, style: style)),
          Expanded(
            flex: 3,
            child: Text(distance, style: style, textAlign: TextAlign.end),
          ),
        ],
      ),
    );
  }
}
