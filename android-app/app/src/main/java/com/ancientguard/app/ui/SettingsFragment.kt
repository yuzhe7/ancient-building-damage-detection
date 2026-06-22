package com.ancientguard.app.ui

import android.content.SharedPreferences
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.preference.PreferenceManager
import com.ancientguard.app.R
import com.ancientguard.app.databinding.FragmentSettingsBinding

class SettingsFragment : Fragment() {
    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!
    private lateinit var prefs: SharedPreferences

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        prefs = PreferenceManager.getDefaultSharedPreferences(requireContext())

        val savedModel = prefs.getString("model_name", "model_nano.tflite") ?: "model_nano.tflite"
        when (savedModel) {
            "model_nano.tflite" -> binding.rbNano.isChecked = true
            "model_small.tflite" -> binding.rbSmall.isChecked = true
            "model_medium.tflite" -> binding.rbMedium.isChecked = true
        }

        binding.rgModel.setOnCheckedChangeListener { _, checkedId ->
            val model = when (checkedId) {
                R.id.rbNano -> "model_nano.tflite"
                R.id.rbSmall -> "model_small.tflite"
                R.id.rbMedium -> "model_medium.tflite"
                else -> "model_nano.tflite"
            }
            prefs.edit().putString("model_name", model).apply()
            Toast.makeText(requireContext(), "模型已切换，下次检测生效", Toast.LENGTH_SHORT).show()
        }

        val savedThreshold = prefs.getFloat("detection_threshold", 0.4f)
        binding.sliderThreshold.value = savedThreshold
        binding.tvThresholdValue.text = "%.2f".format(savedThreshold)

        binding.sliderThreshold.addOnChangeListener { _, value, _ ->
            binding.tvThresholdValue.text = "%.2f".format(value)
            prefs.edit().putFloat("detection_threshold", value).apply()
        }

        binding.btnExport.setOnClickListener {
            Toast.makeText(requireContext(), "导出功能将在下个版本实现", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
