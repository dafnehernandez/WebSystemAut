// TODO JS
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById('archivo');
  const selectBtn = document.getElementById('selectBtn');
  const fileName = document.getElementById('fileName');
  const tipoRadios = document.querySelectorAll('input[name="tipo_reporte"]');

  // Muestra nombre del archivo
  if (selectBtn && input && fileName) {
    selectBtn.addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
      if (input.files.length > 0) {
        fileName.textContent = "Archivo seleccionado: " + input.files[0].name;
      }
    });
  }

  // Activar u ocultar las opciones específicas al seleccionar tipo de reporte
  if (tipoRadios.length) {
    tipoRadios.forEach(radio => {
      radio.addEventListener('change', toggleOpciones);
    });
    toggleOpciones(); // Ejecutar al cargar para reflejar estado inicial
  }
});

// Función para mostrar u ocultar las opciones específicas
function toggleOpciones() {
  const tipo = document.querySelector('input[name="tipo_reporte"]:checked').value;
  const opciones = document.getElementById('opciones-especificas');
  if (opciones) {
    opciones.style.display = (tipo === 'especifico') ? 'block' : 'none';
  }
}
