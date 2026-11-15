"""Залікова робота: облік школи, статистика та зарплати (Python 3.11+)."""
from __future__ import annotations
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent

@dataclass
class Student:
    surname: str
    name: str
    patronymic: str
    birth_year: int
    gender: str
    average_grade: float

@dataclass
class SchoolClass:
    grade: int
    letter: str
    students: list[Student] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f'{self.grade}{self.letter}'

    def promote(self) -> bool:
        """Повертає False, якщо клас випускається зі школи."""
        if self.grade == 11:
            return False
        self.grade += 1
        return True

@dataclass
class Employee:
    full_name: str
    base_salary: float

    def salary(self) -> float:
        raise NotImplementedError('Розрахунок визначається підкласом')

@dataclass
class Teacher(Employee):
    teaching_years: int

    def salary(self) -> float:
        return self.base_salary * self.teaching_years / 30

@dataclass
class Director(Employee):
    teaching_years: int
    management_years: int

    def salary(self) -> float:
        return self.base_salary * self.teaching_years / 50 + self.management_years * 500

@dataclass
class SecurityGuard(Employee):
    work_years: int

    def salary(self) -> float:
        return self.base_salary + self.work_years * 250

@dataclass
class School:
    name: str
    classes: list[SchoolClass] = field(default_factory=list)
    employees: list[Employee] = field(default_factory=list)

    def load_csv(self, classes_file: Path, students_file: Path) -> None:
        self.classes.clear()
        lookup: dict[str, SchoolClass] = {}
        with classes_file.open(encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                obj = SchoolClass(int(row['grade']), row['letter'])
                if not 1 <= obj.grade <= 11 or obj.label in lookup:
                    raise ValueError(f'Некоректний або повторний клас: {obj.label}')
                self.classes.append(obj)
                lookup[obj.label] = obj
        with students_file.open(encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                label = row['class']
                if label not in lookup:
                    raise ValueError(f'Невідомий клас: {label}')
                student = Student(row['surname'], row['name'], row['patronymic'],
                                  int(row['birth_year']), row['gender'], float(row['average_grade']))
                if student.gender not in ('Х', 'Д') or not 0 <= student.average_grade <= 12:
                    raise ValueError(f'Некоректні дані учня: {row}')
                lookup[label].students.append(student)

    def all_students(self) -> list[Student]:
        return [s for c in self.classes for s in c.students]

    def print_statistics(self, heading: str) -> None:
        students = self.all_students()
        n = len(students)
        boys = sum(s.gender == 'Х' for s in students)
        girls = sum(s.gender == 'Д' for s in students)
        print(f'\n{heading}')
        print(f'Кількість учнів: {n}')
        print(f'Хлопці: {boys / n * 100:.1f}%, дівчата: {girls / n * 100:.1f}%' if n else 'Учнів немає')
        print(f'Середня кількість у класі: {n / len(self.classes):.2f}' if self.classes else 'Класів немає')
        if self.classes:
            maximum = max(len(c.students) for c in self.classes)
            minimum = min(len(c.students) for c in self.classes)
            print('Максимум:', maximum, 'у класах', ', '.join(c.label for c in self.classes if len(c.students) == maximum))
            print('Мінімум:', minimum, 'у класах', ', '.join(c.label for c in self.classes if len(c.students) == minimum))

    def plot_statistics(self) -> None:
        out = BASE / 'graphs'
        out.mkdir(exist_ok=True)
        plt.rcParams['font.family'] = 'DejaVu Sans'
        # Підписи латиницею для сумісності з будь-якою ОС.
        by_grade = Counter()
        by_letter: dict[str, list[int]] = defaultdict(list)
        by_year = Counter()
        for c in self.classes:
            by_grade[c.grade] += len(c.students)
            by_letter[c.letter].append(len(c.students))
            for s in c.students:
                by_year[s.birth_year] += 1
        charts = [
            ('01_grades.png', sorted(by_grade), [by_grade[k] for k in sorted(by_grade)], 'Students by grade', 'Grade', 'Students', 'bar'),
            ('02_letters.png', sorted(by_letter), [sum(by_letter[k])/len(by_letter[k]) for k in sorted(by_letter)], 'Average class size by letter', 'Class letter', 'Average students', 'bar'),
            ('03_birth_year.png', sorted(by_year), [by_year[k] for k in sorted(by_year)], 'Students by birth year', 'Birth year', 'Students', 'line'),
        ]
        for filename, xs, ys, title, xlabel, ylabel, kind in charts:
            fig, ax = plt.subplots(figsize=(8, 4.2))
            if kind == 'bar':
                ax.bar([str(x) for x in xs], ys)
            else:
                ax.plot(xs, ys, marker='o')
                ax.set_xticks(xs)
            ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
            ax.grid(axis='y', alpha=.2)
            fig.tight_layout()
            fig.savefig(out / filename, dpi=150)
            plt.close(fig)
        fig, ax = plt.subplots(figsize=(8, 4.2))
        for c in self.classes:
            ax.scatter([c.label] * len(c.students), [s.average_grade for s in c.students], alpha=.65)
        ax.set(title='Student average grade by class', xlabel='Class', ylabel='Average grade', ylim=(0, 12.5))
        ax.grid(axis='y', alpha=.2)
        fig.tight_layout()
        fig.savefig(out / '04_scatter.png', dpi=150)
        plt.close(fig)

    def promote_all(self) -> None:
        self.classes = [c for c in self.classes if c.promote()]

    def save_salaries(self, path: Path) -> None:
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['full_name', 'position', 'salary_uah'])
            for employee in self.employees:
                writer.writerow([employee.full_name, type(employee).__name__, f'{employee.salary():.2f}'])
                print(f'{employee.full_name} ({type(employee).__name__}): {employee.salary():.2f} грн')

def main() -> None:
    school = School('Демонстраційна школа')
    school.load_csv(BASE / 'classes.csv', BASE / 'students.csv')
    school.print_statistics('ДО ПЕРЕВЕДЕННЯ')
    school.plot_statistics()
    school.promote_all()
    school.print_statistics('ПІСЛЯ ПЕРЕВЕДЕННЯ')
    school.employees = [
        Director('Олена Коваль', 15000, 25, 10),
        Teacher('Іван Петренко', 12000, 15),
        Teacher('Марія Бондар', 12000, 24),
        SecurityGuard('Петро Мельник', 11000, 8),
    ]
    print('\nЗАРПЛАТИ')
    school.save_salaries(BASE / 'salaries.csv')
    print('\nГрафіки: graphs/; зарплати: salaries.csv')

if __name__ == '__main__':
    main()
