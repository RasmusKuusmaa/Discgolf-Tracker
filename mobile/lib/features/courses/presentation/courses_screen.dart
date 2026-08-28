import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/geo/haversine.dart';
import '../../../core/widgets/empty_state.dart';
import '../../../core/widgets/loading_indicator.dart';
import '../../../domain/models/course.dart';
import '../../../domain/models/layout.dart';
import '../providers/course_list_controller.dart';
import '../providers/course_list_state.dart';

class CoursesScreen extends ConsumerStatefulWidget {
  const CoursesScreen({super.key});

  @override
  ConsumerState<CoursesScreen> createState() => _CoursesScreenState();
}

class _CoursesScreenState extends ConsumerState<CoursesScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final CourseListState state = ref.watch(courseListControllerProvider);
    final CourseListController controller = ref.read(courseListControllerProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: const Text('Courses')),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: TextField(
                controller: _searchController,
                onChanged: controller.setQuery,
                decoration: InputDecoration(
                  hintText: 'Search courses or cities',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: state.query.isEmpty
                      ? null
                      : IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () {
                            _searchController.clear();
                            controller.setQuery('');
                          },
                        ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: Align(
                alignment: Alignment.centerLeft,
                child: SegmentedButton<CourseSort>(
                  segments: const [
                    ButtonSegment(
                      value: CourseSort.name,
                      label: Text('Name'),
                      icon: Icon(Icons.sort_by_alpha),
                    ),
                    ButtonSegment(
                      value: CourseSort.distance,
                      label: Text('Distance'),
                      icon: Icon(Icons.near_me_outlined),
                    ),
                  ],
                  selected: <CourseSort>{state.sort},
                  onSelectionChanged: (Set<CourseSort> selection) =>
                      controller.setSort(selection.first),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Expanded(child: _buildBody(state)),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(CourseListState state) {
    if (state.isLoading && state.courses.isEmpty) {
      return const LoadingIndicator(message: 'Loading courses…');
    }
    if (state.courses.isEmpty) {
      return EmptyState(
        icon: Icons.golf_course_outlined,
        title: state.query.isEmpty ? 'No courses yet' : 'No courses found',
        message: state.query.isEmpty
            ? 'Courses you create or that sync from the server will show up here.'
            : 'Try a different search term.',
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
      itemCount: state.courses.length,
      itemBuilder: (context, index) {
        final Course course = state.courses[index];
        final double? distanceKm = state.userLatitude == null || state.userLongitude == null
            ? null
            : haversineKm(
                state.userLatitude!,
                state.userLongitude!,
                course.latitude,
                course.longitude,
              );
        return _CourseListItem(course: course, distanceKm: distanceKm);
      },
    );
  }
}

class _CourseListItem extends StatelessWidget {
  const _CourseListItem({required this.course, this.distanceKm});

  final Course course;
  final double? distanceKm;

  Layout? get _primaryLayout {
    if (course.layouts.isEmpty) {
      return null;
    }
    return course.layouts.firstWhere(
      (layout) => layout.isDefault,
      orElse: () => course.layouts.first,
    );
  }

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    final TextTheme textTheme = Theme.of(context).textTheme;
    final String location = [course.city, course.country]
        .where((part) => part != null && part.isNotEmpty)
        .join(', ');
    final Layout? layout = _primaryLayout;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(course.name, style: textTheme.titleMedium),
                ),
                if (distanceKm != null) ...[
                  const SizedBox(width: 8),
                  _Chip(
                    icon: Icons.near_me_outlined,
                    label: _formatDistance(distanceKm!),
                    colorScheme: colorScheme,
                  ),
                ],
              ],
            ),
            if (location.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                location,
                style: textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            if (layout != null) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _Chip(
                    icon: Icons.flag_outlined,
                    label: '${layout.holeCount} holes',
                    colorScheme: colorScheme,
                  ),
                  _Chip(
                    icon: Icons.sports_golf_outlined,
                    label: 'Par ${layout.parTotal}',
                    colorScheme: colorScheme,
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatDistance(double km) {
    if (km < 1) {
      return '${(km * 1000).round()} m';
    }
    return '${km.toStringAsFixed(1)} km';
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.icon, required this.label, required this.colorScheme});

  final IconData icon;
  final String label;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: colorScheme.onSecondaryContainer),
          const SizedBox(width: 4),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: colorScheme.onSecondaryContainer,
            ),
          ),
        ],
      ),
    );
  }
}
