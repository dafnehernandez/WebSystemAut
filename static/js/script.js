// JS para funcionalidad adicional si se desea
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById('archivo');
  const selectBtn = document.getElementById('selectBtn');
  const fileName = document.getElementById('fileName');

  if (selectBtn && input && fileName) {
    selectBtn.addEventListener('click', () => input.click());

    input.addEventListener('change', () => {
      if (input.files.length > 0) {
        fileName.textContent = "Archivo seleccionado: " + input.files[0].name;
      }
    });
  }
});
