import 'package:flutter/material.dart';
import 'package:hb_shared/hb_shared.dart';

/// Vertical progress trail for the happy path of an order. Terminal failure
/// states (rejected/cancelled) are rendered by the caller instead.
class OrderStatusTimeline extends StatelessWidget {
  final OrderStatus status;

  const OrderStatusTimeline({super.key, required this.status});

  static const _steps = [
    (OrderStatus.placed, 'Order placed', 'The stall has been notified'),
    (OrderStatus.accepted, 'Accepted', 'The stall is getting to it'),
    (OrderStatus.preparing, 'Preparing', 'Your food is being cooked'),
    (OrderStatus.ready, 'Ready for pickup', 'Head over and collect it'),
    (OrderStatus.completed, 'Completed', 'Enjoy your meal'),
  ];

  @override
  Widget build(BuildContext context) {
    final currentIndex = _steps.indexWhere((s) => s.$1 == status);

    return Column(
      children: [
        for (var i = 0; i < _steps.length; i++)
          _TimelineRow(
            title: _steps[i].$2,
            subtitle: _steps[i].$3,
            done: i <= currentIndex,
            active: i == currentIndex,
            isLast: i == _steps.length - 1,
          ),
      ],
    );
  }
}

class _TimelineRow extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool done;
  final bool active;
  final bool isLast;

  const _TimelineRow({
    required this.title,
    required this.subtitle,
    required this.done,
    required this.active,
    required this.isLast,
  });

  @override
  Widget build(BuildContext context) {
    final color = done ? AppTheme.primaryRed : AppTheme.divider;

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 22,
                height: 22,
                decoration: BoxDecoration(
                  color: done ? AppTheme.primaryRed : Colors.transparent,
                  border: Border.all(color: color, width: 2),
                  shape: BoxShape.circle,
                ),
                child: done
                    ? const Icon(Icons.check, size: 14, color: Colors.white)
                    : const SizedBox.shrink(),
              ),
              if (!isLast)
                Expanded(
                  child: Container(width: 2, color: color),
                ),
            ],
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 22),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: active ? FontWeight.w800 : FontWeight.w600,
                      color: done ? AppTheme.textPrimary : AppTheme.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: const TextStyle(color: AppTheme.textSecondary, fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
