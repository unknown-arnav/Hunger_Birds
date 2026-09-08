import 'package:flutter/material.dart';
import 'package:hb_shared/hb_shared.dart';
import 'package:provider/provider.dart';

import '../state/merchant_state.dart';

class PendingApprovalScreen extends StatefulWidget {
  const PendingApprovalScreen({super.key});

  @override
  State<PendingApprovalScreen> createState() => _PendingApprovalScreenState();
}

class _PendingApprovalScreenState extends State<PendingApprovalScreen> {
  bool _checking = false;

  Future<void> _check() async {
    setState(() => _checking = true);
    try {
      await context.read<MerchantState>().refreshVendor();
      if (!mounted) return;
      final stage = context.read<MerchantState>().stage;
      if (stage == MerchantStage.awaitingApproval) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Still waiting on admin approval')),
        );
      }
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final vendor = context.watch<MerchantState>().vendor;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pending approval'),
        actions: [
          TextButton(
            onPressed: () => context.read<MerchantState>().logout(),
            child: const Text('Log out'),
          ),
        ],
      ),
      body: EmptyState(
        icon: Icons.hourglass_top,
        title: '${vendor?.stallName ?? 'Your stall'} is under review',
        message: 'An admin needs to approve your stall before students can see it '
            'and place orders. You can set up your menu once approved.',
        action: OutlinedButton(
          onPressed: _checking ? null : _check,
          child: Text(_checking ? 'Checking…' : 'Check again'),
        ),
      ),
    );
  }
}
