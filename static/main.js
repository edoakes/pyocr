var files = [];
var processing = false;

function lambda_post(data, callback) {
  var url = 'https://g5ni3sw220.execute-api.us-west-2.amazonaws.com/prod/OCR'

  $.ajax({
    type: 'POST',
    url: url,
    contentType: 'application/json',
    data: JSON.stringify(data),
    success: callback,
    failure: function(error) {
      alert("Error: " + error + ".  Consider refreshing.")
    }
  });
}

function success(ret) {
  var txt = atob(ret['data']);
  var blob = new Blob([txt], {type:"text/plain;charset=utf-8"});
  download(blob, ret['filename']);
}

function download(blob, name) {
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
}

$(document).ready(function() {
  $("#files").change(function(event) {
    $.each(event.target.files, function(index, file) {
      var reader = new FileReader();
      reader.onload = function(event){
        object = {};
        object.filename = file.name;
        object.data = event.target.result;
        files.push(object);
      };
      reader.onerror = function(event) {
        alert("Failed to read file. Please try again.");
      }
      reader.readAsDataURL(file);
    });
  });

  $("#file-form").submit(function(form) {
    $.each(files, function(index, file) {
      cmd = {'op':'ocr', 'data':file.data, 'filename':file.filename};
      lambda_post(cmd, success);
    });
    files = [];
    form.preventDefault();
    return false;
  });
});