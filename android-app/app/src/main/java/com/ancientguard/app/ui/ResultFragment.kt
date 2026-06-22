package com.ancientguard.app.ui

import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.speech.tts.TextToSpeech
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.navigation.fragment.navArgs
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ancientguard.app.R
import com.ancientguard.app.data.AppDatabase
import com.ancientguard.app.data.Damage
import com.ancientguard.app.data.Inspection
import com.ancientguard.app.databinding.FragmentResultBinding
import com.ancientguard.app.detection.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.util.*

class ResultFragment : Fragment() {
    private var _binding: FragmentResultBinding? = null
    private val binding get() = _binding!!
    private val args: ResultFragmentArgs by navArgs()

    private val detector by lazy { TFLiteDetector(requireContext()) }
    private val renderer = BoundingBoxRenderer()
    private val evaluator = SeverityEvaluator()
    private val advisor = RepairAdvisor()

    private var annotatedBitmap: Bitmap? = null
    private var detectionResults: List<DetectedBox> = emptyList()
    private var severityResults: List<Pair<String, IntArray>> = emptyList()
    private var tts: TextToSpeech? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentResultBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        tts = TextToSpeech(requireContext()) { it ->
            if (it == TextToSpeech.SUCCESS) {
                tts?.language = Locale.CHINESE
            }
        }

        binding.btnBack.setOnClickListener { findNavController().popBackStack() }
        binding.btnSave.setOnClickListener { saveAnnotatedImage() }
        binding.btnShare.setOnClickListener { shareAnnotatedImage() }

        detector.loadModel()

        lifecycleScope.launch {
            val bitmap = withContext(Dispatchers.IO) {
                if (args.isAsset) {
                    val inputStream = requireContext().contentResolver.openInputStream(Uri.parse(args.imagePath))
                    BitmapFactory.decodeStream(inputStream)
                } else BitmapFactory.decodeFile(args.imagePath)
            }

            if (bitmap != null) {
                val scaled = Bitmap.createScaledBitmap(bitmap, 640, 640, true)
                val boxes = detector.detect(scaled)
                detectionResults = boxes
                severityResults = boxes.map { evaluator.evaluate(it) }
                annotatedBitmap = renderer.draw(bitmap, boxes, true)

                withContext(Dispatchers.Main) {
                    binding.ivResult.setImageBitmap(annotatedBitmap)
                    updateStats()
                    setupRecyclerView()
                    speakResults()
                }
                saveToDatabase(boxes, args.imagePath)
            }
        }
    }

    private fun speakResults() {
        val total = detectionResults.size
        val (mild, medium, severe) = evaluator.countBySeverity(severityResults.map { it.first })
        if (total == 0) {
            tts?.speak("未检测到损伤", TextToSpeech.QUEUE_FLUSH, null, "result_0")
            return
        }
        val text = StringBuilder("检测到${total}处损伤。")
        if (severe > 0) text.append("其中${severe}处严重，需立即处理。")
        if (medium > 0) text.append("${medium}处中等。")
        if (mild > 0) text.append("${mild}处轻微。")
        tts?.speak(text.toString(), TextToSpeech.QUEUE_FLUSH, null, "result_$total")
    }

    private fun updateStats() {
        val severities = severityResults.map { it.first }
        val (mild, medium, severe) = evaluator.countBySeverity(severities)
        binding.tvTotalCount.text = "${detectionResults.size}"
        binding.tvMildCount.text = "$mild"
        binding.tvMediumCount.text = "$medium"
        binding.tvSevereCount.text = "$severe"
    }

    private fun setupRecyclerView() {
        binding.rvDamages.layoutManager = LinearLayoutManager(requireContext())
        binding.rvDamages.adapter = DamageAdapter(detectionResults, severityResults,
            onItemClick = { position ->
                (binding.rvDamages.adapter as DamageAdapter).toggleExpanded(position)
            })
    }

    private suspend fun saveToDatabase(boxes: List<DetectedBox>, imagePath: String) {
        withContext(Dispatchers.IO) {
            val db = AppDatabase.getInstance(requireContext())
            val severities = boxes.map { evaluator.evaluate(it) }
            val (mild, medium, severe) = evaluator.countBySeverity(severities.map { it.first })

            val inspection = Inspection(
                imagePath = imagePath,
                totalCount = boxes.size, mildCount = mild,
                mediumCount = medium, severeCount = severe
            )
            db.inspectionDao().insert(inspection)
            val damages = boxes.mapIndexed { i, box ->
                val (severity, _) = severities[i]
                Damage(inspectionId = inspection.id, clsName = box.clsName,
                    confidence = box.confidence, severity = severity,
                    areaPercent = box.areaPercent, x1 = box.x1, y1 = box.y1,
                    x2 = box.x2, y2 = box.y2,
                    advice = advisor.getAdvice(box.clsName, severity))
            }
            db.damageDao().insertAll(damages)
        }
    }

    private fun saveAnnotatedImage() {
        val bitmap = annotatedBitmap ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            val filename = "ancient_guard_${System.currentTimeMillis()}.jpg"
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Images.Media.DISPLAY_NAME, filename)
                    put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                }
                val uri = requireContext().contentResolver.insert(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                uri?.let {
                    requireContext().contentResolver.openOutputStream(it)?.use { out ->
                        bitmap.compress(Bitmap.CompressFormat.JPEG, 95, out)
                    }
                }
            } else {
                val dir = requireContext().externalMediaDirs.first()
                FileOutputStream(File(dir, filename)).use { out ->
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 95, out)
                }
            }
        }
    }

    private fun shareAnnotatedImage() {
        val bitmap = annotatedBitmap ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            val file = File(requireContext().cacheDir, "share_${System.currentTimeMillis()}.jpg")
            FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.JPEG, 95, it) }
            val uri = FileProvider.getUriForFile(requireContext(),
                "${requireContext().packageName}.fileprovider", file)
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "image/jpeg"
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, "分享检测结果"))
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        detector.close()
        tts?.shutdown()
        _binding = null
    }
}

class DamageAdapter(
    private val boxes: List<DetectedBox>,
    private val severities: List<Pair<String, IntArray>>,
    private val onItemClick: (Int) -> Unit
) : RecyclerView.Adapter<DamageAdapter.ViewHolder>() {
    private val advisor = RepairAdvisor()
    private val expanded = mutableSetOf<Int>()

    fun toggleExpanded(position: Int) {
        if (expanded.contains(position)) expanded.remove(position) else expanded.add(position)
        notifyItemChanged(position)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_damage, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val box = boxes[position]
        val (severity, colorArr) = severities[position]
        val advice = advisor.getAdvice(box.clsName, severity)
        holder.severityDot.background.setTint(
            android.graphics.Color.rgb(colorArr[0], colorArr[1], colorArr[2]))
        holder.tvName.text = box.clsName
        holder.tvConfidence.text = "%.1f%%".format(box.confidence * 100)
        holder.tvSeverity.text = severity
        holder.tvArea.text = "面积: %.1f%%".format(box.areaPercent)
        holder.tvAdvice.text = advice
        holder.tvAdvice.maxLines = if (expanded.contains(position)) Int.MAX_VALUE else 2
        holder.itemView.setOnClickListener { onItemClick(position) }
    }

    override fun getItemCount() = boxes.size

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val severityDot: View = view.findViewById(R.id.severityDot)
        val tvName: TextView = view.findViewById(R.id.tvDamageName)
        val tvConfidence: TextView = view.findViewById(R.id.tvConfidence)
        val tvSeverity: TextView = view.findViewById(R.id.tvSeverity)
        val tvArea: TextView = view.findViewById(R.id.tvArea)
        val tvAdvice: TextView = view.findViewById(R.id.tvAdvice)
    }
}
