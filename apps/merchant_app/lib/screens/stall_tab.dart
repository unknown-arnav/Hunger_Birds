import 'package:flutter/material.dart';
import 'package:hb_shared/hb_shared.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../services/cloudinary_uploader.dart';
import '../state/merchant_state.dart';

class StallTab extends StatefulWidget {
  const StallTab({super.key});

  @override
  State<StallTab> createState() => _StallTabState();
}

class _StallTabState extends State<StallTab> {
  bool _uploadingCover = false;

  Future<void> _editDetails() async {
    final merchant = context.read<MerchantState>();
    final nameController = TextEditingController(text: merchant.vendor?.stallName ?? '');
    final descriptionController = TextEditingController(text: merchant.vendor?.description ?? '');

    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Stall details'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: 'Stall name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: descriptionController,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Description'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Save')),
        ],
      ),
    );

    if (saved != true || !mounted) return;
    try {
      await merchant.updateProfile(
        stallName: nameController.text.trim(),
        description: descriptionController.text.trim(),
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _changeCover() async {
    final picked = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1600);
    if (picked == null || !mounted) return;

    setState(() => _uploadingCover = true);
    try {
      final bytes = await picked.readAsBytes();
      if (!mounted) return;
      final url = await CloudinaryUploader(context.read<ApiClient>())
          .upload(bytes: bytes, filename: picked.name);
      if (!mounted) return;
      await context.read<MerchantState>().updateProfile(coverImageUrl: url);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _uploadingCover = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final merchant = context.watch<MerchantState>();
    final vendor = merchant.vendor;

    return Scaffold(
      appBar: AppBar(title: const Text('Your stall')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    vendor?.stallName ?? '',
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
                  ),
                  if (vendor?.description != null && vendor!.description!.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      vendor.description!,
                      style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                    ),
                  ],
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      OutlinedButton.icon(
                        onPressed: _editDetails,
                        icon: const Icon(Icons.edit_outlined, size: 18),
                        label: const Text('Edit'),
                      ),
                      const SizedBox(width: 10),
                      OutlinedButton.icon(
                        onPressed: _uploadingCover ? null : _changeCover,
                        icon: const Icon(Icons.image_outlined, size: 18),
                        label: Text(_uploadingCover ? 'Uploading…' : 'Cover photo'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: SwitchListTile(
              value: vendor?.isOpen ?? false,
              activeThumbColor: AppTheme.success,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              title: const Text(
                'Accepting orders',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
              subtitle: Text(
                (vendor?.isOpen ?? false)
                    ? 'Students can order from you right now'
                    : 'Your stall shows as closed',
                style: const TextStyle(fontSize: 13),
              ),
              onChanged: (value) => context.read<MerchantState>().setOpen(value),
            ),
          ),
          const SizedBox(height: 16),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Row(
                children: [
                  Icon(Icons.payments_outlined, color: AppTheme.textSecondary),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'All orders are cash on delivery. Collect payment when the student picks up.',
                      style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () => context.read<MerchantState>().logout(),
            icon: const Icon(Icons.logout, size: 18),
            label: const Text('Log out'),
          ),
        ],
      ),
    );
  }
}
