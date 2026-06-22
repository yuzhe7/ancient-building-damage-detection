package com.ancientguard.app.detection

import android.content.Context
import android.graphics.Bitmap
import com.ancientguard.app.util.Constants
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.channels.FileChannel

class TFLiteDetector(private val context: Context) {
    private var interpreter: Interpreter? = null
    private var loaded = false

    fun loadModel(modelName: String = "model_nano.tflite"): Boolean {
        return try {
            val assetFd = context.assets.openFd(modelName)
            val inputStream = FileInputStream(assetFd.fileDescriptor)
            val fileChannel = inputStream.channel
            val startOffset = assetFd.startOffset
            val declaredLength = assetFd.declaredLength
            val buffer = fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
            interpreter = Interpreter(buffer)
            assetFd.close()
            inputStream.close()
            loaded = true
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    fun detect(bitmap: Bitmap): List<DetectedBox> {
        val tflite = interpreter ?: return emptyList()
        if (!loaded) return emptyList()

        // Preprocess: resize to 640x640 and normalize
        val scaled = Bitmap.createScaledBitmap(bitmap, Constants.MODEL_INPUT_SIZE, Constants.MODEL_INPUT_SIZE, true)
        val inputBuffer = bitmapToByteBuffer(scaled)

        // Output: (1, 300, 6) -> [batch, boxes, (x1,y1,x2,y2,conf,cls)]
        val outputShape = tflite.getOutputTensor(0).shape()
        val numBoxes = outputShape[1]
        val outputArray = Array(1) { Array(numBoxes) { FloatArray(6) } }

        tflite.run(inputBuffer, outputArray)

        val scaleX = bitmap.width.toFloat() / Constants.MODEL_INPUT_SIZE
        val scaleY = bitmap.height.toFloat() / Constants.MODEL_INPUT_SIZE
        val results = mutableListOf<DetectedBox>()

        for (i in 0 until numBoxes) {
            val row = outputArray[0][i]
            val x1 = row[0]
            val y1 = row[1]
            val x2 = row[2]
            val y2 = row[3]
            val conf = row[4]
            val clsIdx = row[5].toInt()

            if (conf < Constants.DEFAULT_THRESHOLD) continue
            if (clsIdx < 0 || clsIdx >= Constants.CLASS_NAMES.size) continue

            results.add(DetectedBox(
                clsName = Constants.CLASS_NAMES[clsIdx],
                confidence = conf,
                x1 = (x1 * scaleX).toInt().coerceIn(0, bitmap.width),
                y1 = (y1 * scaleY).toInt().coerceIn(0, bitmap.height),
                x2 = (x2 * scaleX).toInt().coerceIn(0, bitmap.width),
                y2 = (y2 * scaleY).toInt().coerceIn(0, bitmap.height)
            ))
        }
        return results
    }

    private fun bitmapToByteBuffer(bitmap: Bitmap): ByteBuffer {
        val size = Constants.MODEL_INPUT_SIZE
        val byteBuffer = ByteBuffer.allocateDirect(4 * 3 * size * size)
        byteBuffer.order(ByteOrder.nativeOrder())
        val floatBuffer = byteBuffer.asFloatBuffer()

        val pixels = IntArray(size * size)
        bitmap.getPixels(pixels, 0, size, 0, 0, size, size)

        for (i in pixels.indices) {
            val pixel = pixels[i]
            floatBuffer.put(i * 3, ((pixel shr 16) and 0xFF) / 255.0f)     // R
            floatBuffer.put(i * 3 + 1, ((pixel shr 8) and 0xFF) / 255.0f)   // G
            floatBuffer.put(i * 3 + 2, (pixel and 0xFF) / 255.0f)           // B
        }
        return byteBuffer
    }

    fun isLoaded() = loaded

    fun close() {
        interpreter?.close()
        interpreter = null
        loaded = false
    }
}
