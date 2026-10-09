// AGP 9.0 tro len co Kotlin tich hop (keo theo KGP 2.2.10), KHONG ap plugin
// `org.jetbrains.kotlin.android` nua — ap vao la build fail ngay.
// https://developer.android.com/build/migrate-to-built-in-kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
}

// Thu muc `build` co hang nghin file nho. Neu du an nam trong thu muc dong bo dam may thi
// nen de build ra ngoai (dong bo cham, file hay bi khoa luc dang ghi).
//
//   TOYDRONE_BUILD_ROOT=D:\build\ToyDroneRemote     (bien moi truong)
//   gradle -PbuildRoot=...                                  (hoac tham so)
//
// Khong dat gi thi build ngay trong thu muc du an nhu thuong.
val buildRoot: String? = (findProperty("buildRoot") as String?)
    ?: System.getenv("TOYDRONE_BUILD_ROOT")

if (!buildRoot.isNullOrBlank()) {
    allprojects {
        layout.buildDirectory.set(file("$buildRoot/${project.path.replace(':', '_').trim('_')}"))
    }
}
