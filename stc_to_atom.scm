(use-modules (opencog))
(use-modules (opencog exec))
(use-modules (json))
(use-modules (ice-9 ftw))
(use-modules (ice-9 format))
(use-modules (ice-9 rdelim))

;; Function to convert a parsed JSON object to Atomese
(define (json->atomese json-obj filename)
  (define (create-atom key value)
    (let ((key-str (if (symbol? key) (symbol->string key) key)))
      (cond
        ((string? value)
         (EvaluationLink
           (PredicateNode key-str)
           (ConceptNode value)))
        ((number? value)
         (EvaluationLink
           (PredicateNode key-str)
           (NumberNode (number->string value))))
        ((boolean? value)
         (EvaluationLink
           (PredicateNode key-str)
           (ConceptNode (if value "true" "false"))))
        ((vector? value)
         (ListLink
           (map (lambda (item)
                  (if (string? item)
                      (ConceptNode item)
                      (create-atom "item" item)))
                (vector->list value))))
        ((list? value)
         (ListLink
           (map (lambda (item)
                  (if (pair? item)
                      (create-atom (car item) (cdr item))
                      (if (string? item)
                          (ConceptNode item)
                          (create-atom "item" item))))
                value)))
        ((pair? value)
         (if (eq? key "authors")
             (ListLink
               (map (lambda (author)
                      (ListLink
                        (EvaluationLink (PredicateNode "given") (ConceptNode (cdr (assoc "given" author))))
                        (EvaluationLink (PredicateNode "family") (ConceptNode (cdr (assoc "family" author))))))
                    value))
             (ListLink (map (lambda (pair) (create-atom (car pair) (cdr pair))) value))))
        ((eq? value 'null)
         (ConceptNode "null"))
        (else (ConceptNode "UnknownType")))))
  
  (if (pair? json-obj)
      (let ((file-node (ConceptNode filename)))
        (ListLink
          file-node
          (map
            (lambda (pair)
              (if (eq? (car pair) 'id)
                  (create-atom "id" (cdr (assoc 'dois (cdr pair))))
                  (create-atom (car pair) (cdr pair))))
            json-obj)))
      (list (ConceptNode "InvalidJSON"))))

;; Global variable to store all book structures
(define all-books '())

;; Function to process a single JSON file
(define (process-json-file filename)
  (catch #t
    (lambda ()
      (let* ((json-string (with-input-from-file filename read-string))
             (json-data (json-string->scm json-string))
             (atomese-data (json->atomese json-data (basename filename))))
        (set! all-books (cons atomese-data all-books))
        (cog-new-atom atomese-data)))
    (lambda (key . args)
      (format #t "Error processing file ~a: ~a~%" filename args))))

;; Function to process all JSON files in a directory
(define (process-json-directory dir-path)
  (ftw dir-path
       (lambda (filename statinfo flag)
         (if (and (eq? flag 'regular)
                  (string-suffix? ".json" filename))
             (begin
               (format #t "Processing file: ~a~%" filename)
               (process-json-file filename)))
         #t)))

;; Main function to run the script
(define (main input-dir output-file)
  ;; Clear the AtomSpace and global book list before processing
  (cog-atomspace-clear)
  (set! all-books '())
  
  ;; Process all JSON files in the input directory
  (format #t "Processing JSON files in directory: ~a~%" input-dir)
  (process-json-directory input-dir)
  
  ;; Create a single ListLink containing all books
  (define all-books-link (ListLink (ConceptNode "AllBooks") (ListLink all-books)))
  (cog-new-atom all-books-link)
  
  ;; Save the AtomSpace to a file
  (let ((port (open-output-file output-file)))
    (for-each (lambda (atom)
                (format port "~a~%" (format #f "~a" atom)))
              (cog-get-all-roots))
    (close-output-port port))
  
  (format #t "AtomSpace graph has been saved to: ~a~%" output-file))