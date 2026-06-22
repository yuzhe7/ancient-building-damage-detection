package com.ancientguard.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.contract.ActivityResultContracts.GetMultipleContents
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.ancientguard.app.databinding.FragmentCameraBinding
import com.ancientguard.app.detection.BoundingBoxRenderer
import com.ancientguard.app.detection.TFLiteDetector
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class CameraFragment : Fragment() {
    private var _binding: FragmentCameraBinding? = null
    private val binding get() = _binding!!

    private var imageCapture: ImageCapture? = null
    private lateinit var cameraExecutor: ExecutorService
    private var lensFacing = CameraSelector.LENS_FACING_BACK
    private var flashOn = false
    private var realtimeMode = false
    private var camera: Camera? = null

    private val detector by lazy { TFLiteDetector(requireContext()) }
    private val renderer = BoundingBoxRenderer()
    private var batchMode = false

    private val singleGalleryLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let { navigateToResult(it.toString(), isAsset = true) }
    }

    private val multiGalleryLauncher = registerForActivityResult(
        GetMultipleContents()
    ) { uris: List<Uri> ->
        if (uris.isNotEmpty()) {
            lifecycleScope.launch(Dispatchers.IO) {
                var count = 0
                for (uri in uris) {
                    val inputStream = requireContext().contentResolver.openInputStream(uri)
                    val bitmap = android.graphics.BitmapFactory.decodeStream(inputStream)
                    inputStream?.close()
                    if (bitmap != null) {
                        val scaled = Bitmap.createScaledBitmap(bitmap, 640, 640, true)
                        val boxes = detector.detect(scaled)
                        count += boxes.size
                    }
                }
                withContext(Dispatchers.Main) {
                    Toast.makeText(requireContext(),
                        "批量完成: ${uris.size} 张图, 共 ${count} 处损伤", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentCameraBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        cameraExecutor = Executors.newSingleThreadExecutor()
        detector.loadModel()

        if (allPermissionsGranted()) startCamera()
        else requestPermissions(arrayOf(Manifest.permission.CAMERA), PERMISSION_REQUEST_CODE)

        binding.btnCapture.setOnClickListener {
            if (realtimeMode) {
                realtimeMode = false
                binding.tvMode.text = "📷"
                startCamera()
            } else takePhoto()
        }
        binding.btnCapture.setOnLongClickListener {
            batchMode = !batchMode
            binding.tvMode.text = if (batchMode) "📁批量" else if (realtimeMode) "🔴实时" else "📷"
            Toast.makeText(requireContext(),
                if (batchMode) "批量模式: 选多张照片" else "单张模式", Toast.LENGTH_SHORT).show()
            true
        }
        binding.btnGallery.setOnClickListener {
            if (batchMode) multiGalleryLauncher.launch("image/*")
            else singleGalleryLauncher.launch("image/*")
        }
        binding.btnFlip.setOnClickListener {
            lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK)
                CameraSelector.LENS_FACING_FRONT else CameraSelector.LENS_FACING_BACK
            startCamera()
        }
        binding.btnFlash.setOnClickListener {
            flashOn = !flashOn
            binding.btnFlash.setImageResource(
                if (flashOn) android.R.drawable.ic_lock_idle_low_battery
                else android.R.drawable.ic_lock_idle_alarm
            )
            startCamera()
        }
        binding.btnRealtime.setOnClickListener {
            realtimeMode = !realtimeMode
            binding.tvMode.text = if (realtimeMode) "🔴实时" else "📷"
            startCamera()
        }
    }

    private fun takePhoto() {
        val imageCapture = this.imageCapture ?: return
        val photoFile = File(
            requireContext().externalMediaDirs.first(),
            "ancient_guard_${System.currentTimeMillis()}.jpg"
        )
        val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()
        imageCapture.takePicture(outputOptions,
            ContextCompat.getMainExecutor(requireContext()),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    navigateToResult(photoFile.absolutePath, isAsset = false)
                }
                override fun onError(exc: ImageCaptureException) {
                    Toast.makeText(requireContext(), "拍照失败: ${exc.message}", Toast.LENGTH_SHORT).show()
                }
            })
    }

    private fun navigateToResult(imagePath: String, isAsset: Boolean) {
        val action = CameraFragmentDirections.actionCameraToResult(imagePath, isAsset)
        findNavController().navigate(action)
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(requireContext())
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.viewFinder.surfaceProvider)
            }
            imageCapture = ImageCapture.Builder()
                .setFlashMode(if (flashOn) ImageCapture.FLASH_MODE_ON else ImageCapture.FLASH_MODE_OFF)
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .build()

            val cameraSelector = CameraSelector.Builder()
                .requireLensFacing(lensFacing).build()

            try {
                cameraProvider.unbindAll()
                if (realtimeMode) {
                    val imageAnalysis = ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build()
                    imageAnalysis.setAnalyzer(cameraExecutor) { imageProxy ->
                        val mediaImage = imageProxy.image
                        if (mediaImage != null) {
                            val yBuffer = mediaImage.planes[0].buffer
                            val yBytes = ByteArray(yBuffer.remaining())
                            yBuffer.get(yBytes)
                            yBuffer.rewind()
                            val bitmap = Bitmap.createBitmap(mediaImage.width, mediaImage.height, Bitmap.Config.ARGB_8888)
                            // Simple Y-only conversion for preview
                            val pixels = IntArray(mediaImage.width * mediaImage.height)
                            for (i in pixels.indices) {
                                val y = yBytes[i].toInt() and 0xFF
                                pixels[i] = 0xFF000000.toInt() or (y shl 16) or (y shl 8) or y
                            }
                            bitmap.setPixels(pixels, 0, mediaImage.width, 0, 0, mediaImage.width, mediaImage.height)
                            val scaled = Bitmap.createScaledBitmap(bitmap, 640, 640, true)
                            val boxes = detector.detect(scaled)
                            lifecycleScope.launch(Dispatchers.Main) {
                        val severeCount = boxes.count { box ->
                            val t = com.ancientguard.app.util.Constants.SEVERITY_THRESHOLDS[box.clsName]
                            t != null && box.areaPercent >= t.second
                        }
                        if (severeCount > 0 || boxes.isNotEmpty()) {
                            binding.tvHint.text = if (severeCount > 0)
                                "⚠ 严重:$severeCount 处 | 总:${boxes.size}处"
                            else "总:${boxes.size}处损伤"
                        } else {
                            binding.tvHint.text = "未检测到损伤"
                        }
                    }
                        }
                        imageProxy.close()
                    }
                    camera = cameraProvider.bindToLifecycle(
                        viewLifecycleOwner, cameraSelector, preview, imageCapture, imageAnalysis)
                } else {
                    camera = cameraProvider.bindToLifecycle(
                        viewLifecycleOwner, cameraSelector, preview, imageCapture)
                }
            } catch (exc: Exception) {
                Toast.makeText(requireContext(), "相机启动失败: ${exc.message}", Toast.LENGTH_SHORT).show()
            }
        }, ContextCompat.getMainExecutor(requireContext()))
    }

    private fun allPermissionsGranted() =
        ContextCompat.checkSelfPermission(requireContext(), Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) startCamera()
            else Toast.makeText(requireContext(), "需要相机权限", Toast.LENGTH_LONG).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        cameraExecutor.shutdown()
        detector.close()
        _binding = null
    }

    companion object { private const val PERMISSION_REQUEST_CODE = 1001 }
}
