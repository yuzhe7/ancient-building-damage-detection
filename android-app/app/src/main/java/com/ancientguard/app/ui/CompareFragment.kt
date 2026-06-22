package com.ancientguard.app.ui

import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.navigation.fragment.navArgs
import com.ancientguard.app.data.AppDatabase
import com.ancientguard.app.databinding.FragmentCompareBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class CompareFragment : Fragment() {
    private var _binding: FragmentCompareBinding? = null
    private val binding get() = _binding!!
    private val args: CompareFragmentArgs by navArgs()

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentCompareBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnBackCompare.setOnClickListener { findNavController().popBackStack() }

        lifecycleScope.launch {
            val db = AppDatabase.getInstance(requireContext())
            val before = withContext(Dispatchers.IO) { db.inspectionDao().getById(args.beforeId) }
            val after = withContext(Dispatchers.IO) { db.inspectionDao().getById(args.afterId) }

            if (before != null) {
                val bmp = withContext(Dispatchers.IO) {
                    BitmapFactory.decodeFile(before.imagePath)
                }
                binding.ivBefore.setImageBitmap(bmp)
            }

            if (after != null) {
                val bmp = withContext(Dispatchers.IO) {
                    BitmapFactory.decodeFile(after.imagePath)
                }
                binding.ivAfter.setImageBitmap(bmp)
            }

            if (before != null && after != null) {
                val diff = after.totalCount - before.totalCount
                val sevChange = after.severeCount - before.severeCount
                binding.tvCompareSummary.text = when {
                    diff < 0 -> "损伤总数减少 ${-diff} 处 ✅"
                    diff > 0 -> "损伤总数增加 $diff 处 ⚠"
                    else -> "损伤总数不变"
                }
                binding.tvCompareDetail.text = buildString {
                    append("修复前: ${before.totalCount}处 (轻微${before.mildCount}/中等${before.mediumCount}/严重${before.severeCount})\n")
                    append("修复后: ${after.totalCount}处 (轻微${after.mildCount}/中等${after.mediumCount}/严重${after.severeCount})\n")
                    if (sevChange < 0) append("严重损伤减少 ${-sevChange} 处，修复有效！")
                    else if (sevChange > 0) append("⚠ 严重损伤增加，需关注！")
                    else append("严重损伤数量不变")
                }
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
