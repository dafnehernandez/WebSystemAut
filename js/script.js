//document.getElementById('btnSeleccionar').addEventListener('click', function() {
//    alert('¡Hola! Este es un mensaje desde js.');
//  }); 
document.addEventListener("DOMContentLoaded", () => {
  const uploadBtn = document.getElementById('uploadBtn');
  const fileInput = document.getElementById('fileInput');
  const fileNameDisplay = document.getElementById('fileName');

  uploadBtn.addEventListener('click', () => {
    fileInput.click();
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      fileNameDisplay.textContent = `Archivo seleccionado: ${fileInput.files[0].name}`;
    }
  });
});

