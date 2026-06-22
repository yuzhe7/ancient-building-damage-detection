package com.ancientguard.app.ui

import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ancientguard.app.R
import com.ancientguard.app.data.AppDatabase
import com.ancientguard.app.data.Inspection
import com.ancientguard.app.databinding.FragmentHistoryBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.*

class HistoryFragment : Fragment() {
    private var _binding: FragmentHistoryBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHistoryBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val db = AppDatabase.getInstance(requireContext())
        val adapter = HistoryAdapter { inspection ->
            val action = HistoryFragmentDirections.actionHistoryToResult(inspection.imagePath, false)
            findNavController().navigate(action)
        }

        binding.rvHistory.layoutManager = LinearLayoutManager(requireContext())
        binding.rvHistory.adapter = adapter

        lifecycleScope.launch {
            db.inspectionDao().getAllByDateDesc().collectLatest { inspections ->
                val grouped = inspections.groupBy {
                    SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date(it.timestamp))
                }.toList().sortedByDescending { (date, _) -> date }
                adapter.submitList(grouped)
            }
        }

        binding.btnClearAll.setOnClickListener {
            AlertDialog.Builder(requireContext())
                .setTitle("确认清空")
                .setMessage("将删除全部检测记录，此操作不可撤销。")
                .setPositiveButton("确认") { _, _ ->
                    lifecycleScope.launch(Dispatchers.IO) { db.inspectionDao().deleteAll() }
                }
                .setNegativeButton("取消", null).show()
        }

        binding.btnExport.setOnClickListener {
            lifecycleScope.launch(Dispatchers.IO) {
                val list = db.inspectionDao().getAllByDateDesc().first()
                exportToCsv(list)
            }
        }
    }

    private suspend fun exportToCsv(inspections: List<Inspection>) {
        withContext(Dispatchers.IO) {
            val file = File(requireContext().cacheDir, "检测记录_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())}.csv")
            FileWriter(file).use { writer ->
                writer.write("﻿") // BOM for Chinese Excel
                writer.write("日期,时间,损伤总数,轻微,中等,严重,模型\n")
                val sdf = SimpleDateFormat("yyyy-MM-dd,HH:mm:ss", Locale.getDefault())
                for (insp in inspections) {
                    writer.write("${sdf.format(Date(insp.timestamp))},${insp.totalCount},${insp.mildCount},${insp.mediumCount},${insp.severeCount},${insp.modelName}\n")
                }
            }
            withContext(Dispatchers.Main) {
                val uri = FileProvider.getUriForFile(requireContext(),
                    "${requireContext().packageName}.fileprovider", file)
                val intent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/csv"
                    putExtra(Intent.EXTRA_STREAM, uri)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
                startActivity(Intent.createChooser(intent, "导出Excel"))
                Toast.makeText(requireContext(), "已导出 ${inspections.size} 条记录", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}

class HistoryAdapter(
    private val onItemClick: (Inspection) -> Unit
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
    private var items: List<Any> = emptyList()

    companion object { private const val TYPE_HEADER = 0; private const val TYPE_ITEM = 1 }

    fun submitList(grouped: List<Pair<String, List<Inspection>>>) {
        val flat = mutableListOf<Any>()
        for ((date, inspections) in grouped) { flat.add(date); flat.addAll(inspections) }
        items = flat; notifyDataSetChanged()
    }

    override fun getItemViewType(position: Int) =
        if (items[position] is String) TYPE_HEADER else TYPE_ITEM

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return if (viewType == TYPE_HEADER) {
            val v = inflater.inflate(android.R.layout.simple_list_item_1, parent, false)
            object : RecyclerView.ViewHolder(v) {
                val tv: TextView = v.findViewById(android.R.id.text1)
            }
        } else {
            InspectionViewHolder(inflater.inflate(R.layout.item_history_child, parent, false))
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val item = items[position]
        when {
            item is String -> {
                val tv = (holder.itemView as? TextView) ?: holder.itemView.findViewById<TextView>(android.R.id.text1)
                tv.text = item; tv.setPadding(16, 16, 16, 4)
                tv.textSize = 14f; tv.setTextColor(0xFF888888.toInt())
            }
            item is Inspection -> {
                (holder as InspectionViewHolder).bind(item)
                holder.itemView.setOnClickListener { onItemClick(item) }
            }
        }
    }

    override fun getItemCount() = items.size

    class InspectionViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val ivThumb: ImageView = view.findViewById(R.id.ivThumbnail)
        private val tvSummary: TextView = view.findViewById(R.id.tvSummary)
        private val tvSeverity: TextView = view.findViewById(R.id.tvSeveritySummary)
        private val tvTime: TextView = view.findViewById(R.id.tvTime)

        fun bind(inspection: Inspection) {
            tvSummary.text = "损伤总数: ${inspection.totalCount}"
            tvSeverity.text = "轻微:${inspection.mildCount} 中等:${inspection.mediumCount} 严重:${inspection.severeCount}"
            tvTime.text = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(inspection.timestamp))
            val file = File(inspection.imagePath)
            if (file.exists()) ivThumb.setImageBitmap(BitmapFactory.decodeFile(inspection.imagePath))
        }
    }
}
