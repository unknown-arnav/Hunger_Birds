import 'dart:convert';

import 'package:hb_shared/hb_shared.dart';
import 'package:http/http.dart' as http;

/// Uploads straight from the device to Cloudinary using a short-lived
/// signature minted by our backend, so image bytes never pass through it.
class CloudinaryUploader {
  final ApiClient api;

  const CloudinaryUploader(this.api);

  Future<String> upload({required List<int> bytes, required String filename}) async {
    final signature = await api.uploadSignature();

    final request = http.MultipartRequest(
      'POST',
      Uri.parse('https://api.cloudinary.com/v1_1/${signature.cloudName}/image/upload'),
    )
      ..fields['api_key'] = signature.apiKey
      ..fields['timestamp'] = signature.timestamp.toString()
      ..fields['signature'] = signature.signature
      ..fields['folder'] = signature.folder
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: filename));

    final streamed = await request.send();
    final body = await streamed.stream.bytesToString();

    if (streamed.statusCode < 200 || streamed.statusCode >= 300) {
      throw ApiException(streamed.statusCode, 'Image upload failed');
    }
    return (jsonDecode(body) as Map<String, dynamic>)['secure_url'] as String;
  }
}
